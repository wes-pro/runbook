import os
import logging
import argparse
import time
import pyperclip
import hmac
import toml
import streamlit as st
from streamlit_shortcuts import add_keyboard_shortcuts

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('-f', '--config-file', action='append', help='Specify commands file definition file')
parser.add_argument('-s', '--session-name', help='Name of Zellij session to which connect to')
parser.add_argument('-p', '--password', default=False, action=argparse.BooleanOptionalAction, help='Enable password protection')
parser.add_argument('-d', '--debug', default=False, action=argparse.BooleanOptionalAction, help='Enable local debugging')

args = parser.parse_args()

if args.debug:
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO

logger = logging.getLogger()
logging.basicConfig(format='%(levelname)s:%(message)s', level=loglevel)

st.set_page_config(page_title="RunBook", layout="centered", initial_sidebar_state="collapsed", menu_items={})


#@st.cache_resource
def load_command_files():
    cmd_series = {}
    for filename in args.config_file:
        logger.info(f'Loading commands from {filename}')
        with open(filename, 'r') as file:
            cmds = toml.load(file)
            cmd_series[cmds['name']] = cmds
    logger.info(f'Successfully loaded following command series: {', '.join(cmd_series.keys())}')
    return cmd_series


def check_password():

    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


def zellij_run_command(cmd, lang=None):
    cmd = cmd.strip().splitlines()
    for i, line in enumerate(cmd):
        line_bytes = ' '.join([str(b) for b in list(line.encode())])
        if exec_button or i < len(cmd) - 1:
            line_bytes += ' 10'
        zcmd = f'zellij --session "{args.session_name}" action write {line_bytes}'
        os.system(zcmd)
        if lang and lang == 'bash':
            time.sleep(0.2)


def zellij_prev_tab():
    zcmd = f'zellij --session "{args.session_name}" action go-to-previous-tab'
    os.system(zcmd)


def zellij_next_tab():
    zcmd = f'zellij --session "{args.session_name}" action go-to-next-tab'
    os.system(zcmd)


def zellij_prev_pane():
    zcmd = f'zellij --session "{args.session_name}" action focus-previous-pane'
    os.system(zcmd)


def zellij_next_pane():
    zcmd = f'zellij --session "{args.session_name}" action focus-next-pane'
    os.system(zcmd)


def zellij_toggle_sync_tab():
    zcmd = f'zellij --session "{args.session_name}" action toggle-active-sync-tab'
    os.system(zcmd)


def zellij_toogle_fullscreen():
    zcmd = f'zellij --session "{args.session_name}" action toggle-fullscreen'
    os.system(zcmd)


def zellij_scroll_up():
    for i in range(20):
        zcmd = f'zellij --session "{args.session_name}" action scroll-up'
        os.system(zcmd)


def zellij_scroll_down():
    for i in range(20):
        zcmd = f'zellij --session "{args.session_name}" action scroll-down'
        os.system(zcmd)


def zellij_ctrl_c():
    zcmd = f'zellij --session "{args.session_name}" action write-chars \"\x03\n\"'
    os.system(zcmd)


def zellij_clear_screen():
    if st.session_state.curr_command['lang'] == 'sql':
        zellij_ctrl_c()
        #zcmd = f'zellij --session "{args.session_name}" action write-chars \"\x03\n\"'
        #os.system(zcmd)
        cmd = "clear screen\n"
    else:
        cmd = "clear\n"
    zcmd = f'zellij --session "{args.session_name}" action write-chars \"{cmd}\"'
    os.system(zcmd)


def zellij_enter():
    zcmd = f'zellij --session "{args.session_name}" action write-chars \"\n\"'
    os.system(zcmd)


def select_next_cmd():
    curr_cmd_index = st.session_state.curr_series['commands'].index(st.session_state.curr_command)
    if exec_button or insert_on_move:
        zellij_run_command(st.session_state.curr_command['cmd'], lang=st.session_state.curr_command['lang'])
    if curr_cmd_index < len(st.session_state.curr_series['commands']) - 1:
        st.session_state.curr_command = st.session_state.curr_series['commands'][curr_cmd_index+1]


def select_prev_cmd():
    curr_cmd_index = st.session_state.curr_series['commands'].index(st.session_state.curr_command)
    if curr_cmd_index > 0:
        st.session_state.curr_command = st.session_state.curr_series['commands'][curr_cmd_index-1]


def update_selection(curr_series, curr_command, execute=False, undo=False):
    st.session_state.curr_series = curr_series
    st.session_state.curr_command = curr_command
    if execute:
        if args.session_name:
            if undo:
                if 'undo' in curr_command:
                    logger.debug(f"About to execute below Zellij command into session {args.session_name}:\n{curr_command['undo']}")
                    pyperclip.copy(curr_command['undo'])
                    zellij_run_command(curr_command['undo'])
            else:
                logger.debug(f"About to execute below Zellij command into session {args.session_name}:\n{curr_command['cmd']}")
                pyperclip.copy(curr_command['cmd'])
                zellij_run_command(curr_command['cmd'], lang=st.session_state.curr_command['lang'])
        else:
            logger.error("Can't run Zellij command without session name")


def render_command_table(cmd_series):
    curr_cmd_index = st.session_state.curr_series['commands'].index(st.session_state.curr_command)
    if cmd_series['name'] not in st.session_state.sel_helpers:
        st.session_state.sel_helpers[cmd_series['name']] = []
    with st.container(height=330):
        for i, cmd in enumerate(cmd_series['commands']):
            if len(search) >= 3 and search.lower() not in cmd['name'].lower():
                continue
            col0, col1, col2, col3 = st.columns([1, 1, 1, 1], vertical_alignment='center', gap='small')
            with col0:
                empty = st.empty()
                st.session_state.sel_helpers[cmd_series['name']].append(empty)
                if cmd_series == st.session_state.curr_series and i == curr_cmd_index:
                    empty.markdown(':material/chevron_right:')

            with col1:
                with st.container(key=f'cmd_lang_{cmd['lang']}-{cmd_series['name']}-{i}'):
                    st.button(cmd['name'], key=f'{cmd_series['name']}-copy-{i}', on_click=update_selection, args=(cmd_series, cmd))
            with col2:
                st.button('', icon=':material/directions_run:', key=f'{cmd_series['name']}-exec-{i}', on_click=update_selection, args=(cmd_series, cmd, True))
            with col3:
                if 'undo' in cmd:
                    st.button('', icon=':material/undo:', key=f'{cmd_series['name']}-undo-{i}', on_click=update_selection, args=(cmd_series, cmd, True, True))


if args.password and not check_password():
    st.stop()

series = load_command_files()

if 'curr_command' not in st.session_state:
    st.session_state.curr_series = list(series.values())[0]
    st.session_state.curr_command = list(series.values())[0]['commands'][0]
    st.session_state.search_string = ''
    st.session_state.sel_helpers = {}

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style.css'), 'r') as file:
    st.markdown(f'<style>{file.read()}</style>', unsafe_allow_html=True)

with st.container(key='header'):
    col_title, col_search = st.columns([1,1], vertical_alignment='center')
    with col_title:
        st.markdown('##### :blue[RunBook]')
    with col_search:
        search = st.text_input('Search', key='search', placeholder='search commands ...', label_visibility='collapsed')

with st.container(key='cmd_list'):
    tabs = st.tabs(series.keys())
    for i, s in enumerate(series.values()):
        with tabs[i]:
            render_command_table(s)

'---'
with st.container(key='remote'):
    col_r11, col_r12, col_r13, col_r14 = st.columns([1,1,1,1], vertical_alignment='center')

    with col_r11:
        exec_button = st.checkbox('AutoExec')
    with col_r12:
        st.button('', icon=':material/arrow_circle_left:', key='tab_left', use_container_width=True, on_click=zellij_prev_tab)
    with col_r13:
        st.button('', icon=':material/arrow_circle_right:', key='tab_right', use_container_width=True, on_click=zellij_next_tab)
    with col_r14:
        if exec_button:
            st.button('select_right', icon=':material/start:', key='select_right', type='primary', use_container_width=True, on_click=select_next_cmd)
        else:
            st.button('select_right', icon=':material/start:', key='select_right', use_container_width=True, on_click=select_next_cmd)

    col_r21, col_r22, col_r23, col_r24 = st.columns([1,1,1,1], vertical_alignment='center')
    with col_r21:
        insert_on_move = st.checkbox('AutoInsert')
    with col_r22:
        st.button('', icon=':material/keyboard_double_arrow_left:', key='pane_left', use_container_width=True, on_click=zellij_prev_pane)
    with col_r23:
        st.button('', icon=':material/keyboard_double_arrow_right:', key='pane_right', use_container_width=True, on_click=zellij_next_pane)
    with col_r24:
        if exec_button:
            st.button('select_enter', icon=':material/keyboard_return:', key='select_enter', type='secondary', use_container_width=True, on_click=zellij_enter)
        else:
            st.button('select_enter', icon=':material/keyboard_return:', key='select_enter', type='primary', use_container_width=True, on_click=zellij_enter)

    '---'

    col_r31, col_r32, col_r33, col_r34 = st.columns([1,1,1,1], vertical_alignment='center')
    with col_r31:
        pass
    with col_r32:
        st.button('', icon=':material/more_down:', key='more_down', use_container_width=True, on_click=zellij_scroll_down)
    with col_r33:
        st.button('', icon=':material/more_up:', key='more_up', use_container_width=True, on_click=zellij_scroll_up)
    with col_r34:
        with st.container(key='cancel'):
            st.button('ctrl_c', icon=':material/cancel:', key='ctrl_c', use_container_width=True, on_click=zellij_ctrl_c)

    col_r41, col_r42, col_r43, col_r44 = st.columns([1,1,1,1], vertical_alignment='center')
    with col_r41:
        st.button('', icon=':material/mop:', use_container_width=True, key='clear_screen', on_click=zellij_clear_screen)
    with col_r42:
        st.button('', icon=':material/fullscreen:', key='fullscreen', use_container_width=True, on_click=zellij_toogle_fullscreen)
    with col_r43:
        st.button('', icon=':material/sync:', key='toogle_tab_sync', use_container_width=True, on_click=zellij_toggle_sync_tab)
    with col_r44:
        st.button('select_left', icon=':material/keyboard_tab_rtl:', key='select_left', use_container_width=True, on_click=select_prev_cmd)


'---'

with st.container(key='cmd_content', height=400):
    st.code(st.session_state.curr_command['cmd'], language=st.session_state.curr_command['lang'])

#add_keyboard_shortcuts({"ArrowRight": "select_right", "ArrowLeft": "select_left"})
add_keyboard_shortcuts({"PageDown": "select_right", "PageUp": "select_left", "Enter": "select_enter", "Home": "ctrl_c"})
