import os
import logging
import argparse
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


@st.cache_resource
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


def zellij_run_command(cmd):
    cmd = cmd.replace('$', '\\$')
    zcmd = f'zellij --session "{args.session_name}" action write-chars \"{cmd}\"'
    os.system(zcmd)


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


def zellij_clear_screen():
    if st.session_state.curr_command['lang'] == 'sql':
        cmd = "clear screen\n"
    else:
        cmd = "clear\n"
    zcmd = f'zellij --session "{args.session_name}" action write-chars \"{cmd}\"'
    os.system(zcmd)


def select_next_cmd(execute=False):
    curr_cmd_index = st.session_state.curr_series['commands'].index(st.session_state.curr_command)
    if exec_button:
        zellij_run_command(st.session_state.curr_command['cmd'])
    if curr_cmd_index < len(st.session_state.curr_series['commands']) - 1:
        st.session_state.curr_command = st.session_state.curr_series['commands'][curr_cmd_index+1]


def select_prev_cmd(execute=False):
    curr_cmd_index = st.session_state.curr_series['commands'].index(st.session_state.curr_command)
    if curr_cmd_index > 0:
        st.session_state.curr_command = st.session_state.curr_series['commands'][curr_cmd_index-1]


def update_selection(curr_series, curr_command, execute=False, undo=False):
    st.session_state.curr_series = curr_series
    st.session_state.curr_command = curr_command
    if execute:
        if args.session_name:
            if undo:
                if 'rcmd' in curr_command:
                    logger.debug(f"About to execute below Zellij command into session {args.session_name}:\n{curr_command['rcmd']}")
                    pyperclip.copy(curr_command['rcmd'])
                    zellij_run_command(curr_command['rcmd'])
            else:
                logger.debug(f"About to execute below Zellij command into session {args.session_name}:\n{curr_command['cmd']}")
                pyperclip.copy(curr_command['cmd'])
                zellij_run_command(curr_command['cmd'])
        else:
            logger.error("Can't run Zellij command without session name")


def render_command_table(cmd_series):
    curr_cmd_index = st.session_state.curr_series['commands'].index(st.session_state.curr_command)
    if cmd_series['name'] not in st.session_state.sel_helpers:
        st.session_state.sel_helpers[cmd_series['name']] = []
    with st.container(height=300):
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
                st.button(cmd['name'], key=f'{cmd_series['name']}-copy-{i}', on_click=update_selection, args=(cmd_series, cmd))
            with col2:
                st.button('', icon=':material/directions_run:', key=f'{cmd_series['name']}-exec-{i}', on_click=update_selection, args=(cmd_series, cmd, True))
            with col3:
                if 'rcmd' in cmd:
                    st.button('', icon=':material/undo:', key=f'{cmd_series['name']}-undo-{i}', on_click=update_selection, args=(cmd_series, cmd, True, True))


if args.password and not check_password():
    st.stop()

series = load_command_files()

if 'curr_command' not in st.session_state:
    st.session_state.curr_series = list(series.values())[0]
    st.session_state.curr_command = list(series.values())[0]['commands'][0]
    st.session_state.search_string = ''
    st.session_state.sel_helpers = {}

with open('style.css', 'r') as file:
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
    col_exec_checkbox, col_tab, col_pane, _, col_select = st.columns([1,1,1,1,1], vertical_alignment='center')
    with col_exec_checkbox:
        with st.container(key='col_exec'):
            exec_button = st.checkbox('AutoExec')
            st.button('Clear screen', icon=':material/mop:', key='clear', on_click=zellij_clear_screen)
    with col_tab:
        st.button('', icon=':material/arrow_circle_left:', key='tab_left', on_click=zellij_prev_tab)
        st.button('', icon=':material/keyboard_double_arrow_left:', key='pane_left', on_click=zellij_prev_pane)
    with col_pane:
        st.button('', icon=':material/arrow_circle_right:', key='tab_right', on_click=zellij_next_tab)
        st.button('', icon=':material/keyboard_double_arrow_right:', key='pane_right', on_click=zellij_next_pane)
    with col_select:
        st.button('select_right', icon=':material/start:', key='select_right', on_click=select_next_cmd)
        st.button('select_left', icon=':material/keyboard_tab_rtl:', key='select_left', on_click=select_prev_cmd)
'---'

with st.container(key='cmd_content', height=200):
    st.code(st.session_state.curr_command['cmd'], language=st.session_state.curr_command['lang'])

add_keyboard_shortcuts({"ArrowRight": "select_right", "ArrowLeft": "select_left"})
