import os
import cmd
import random
import string
import tempfile
import argparse
import inspect

from subprocess import call
from threading import Thread

import zmq
from vexmessage import decode_vex_message

from vexbot import __version__
from vexbot.util import start_vexbot, create_vexdir
from vexbot.adapters.messaging import ZmqMessaging
from vexbot.adapters.command_parser import CommandParser
# from vexbot.adapters.commands.call_editor import call_editor


class Shell(cmd.Cmd):
    def __init__(self,
                 context=None,
                 prompt_name='vexbot',
                 publish_address=None,
                 subscribe_address=None,
                 **kwargs):

        super().__init__()
        self.messaging = ZmqMessaging('command_line',
                                      publish_address,
                                      subscribe_address)

        self.command_parser = CommandParser(self.messaging)
        self.stdout.write('Vexbot {}\n'.format(__version__))
        self.stdout.write('Type \"help\" for available commands\n')
        if kwargs.get('already_running', False):
            self.stdout.write('vexbot already running\n')

        self.command_parser.register_command('start vexbot',
                                             start_vexbot)

        # self.messaging.set_socket_identity('shell')
        self.messaging.set_socket_filter('')
        self.messaging.start_messaging()

        self.prompt = prompt_name + ': '
        self.misc_header = "Commands"
        self._exit_loop = False

    def default(self, arg):
        if not self.command_parser.is_command(arg, call_command=True):
            self.messaging.send_command(arg)

    def run(self):
        frame = None
        while True and not self._exit_loop:
            try:
                frame = self.messaging.sub_socket.recv_multipart(zmq.NOBLOCK)
            except zmq.error.ZMQError:
                pass

            if frame:
                message = decode_vex_message(frame)
                self.stdout.write('\n')
                self.stdout.write(''.join(message.contents))
                self.stdout.write('\n')
                self.stdout.write('vexbot: ')
                frame = None

    def _create_command_function(self, command):
        def resulting_function(arg):
            self.default(' '.join((command, arg)))
        return resulting_function

    def do_EOF(self, arg):
        self.stdout.write('\n')
        self._exit_loop = True
        return True

    def get_names(self):
        return dir(self)

    def do_help(self, arg):
        if arg:
            # TODO
            pass
        else:
            self.stdout.write("{}\n".format(self.doc_leader))
            # TODO
            self.print_topics(self.misc_header,
                              ['start', 'restart', 'kill', 'killall',
                               'list', 'commands', 'alive', 'record',
                               'restartbot'],
                              15,
                              80)

    def add_completion(self, command):
        setattr(self,
                'do_{}'.format(command),
                self._create_command_function(command))

    """
    def _call_editor(self):
        # TODO: move into command function
        vexdir = create_vexdir()
        code_output = call_editor(vexdir)
        try:
            code = compile(code_output, '<string>', 'exec')
        except Exception as e:
            print(e)

        local = {}
        exec(code, globals(), local)
        # need to add to commands?
        for k, v in local.items():
            if inspect.isfunction(v):
                self.command_parser.register_command(k, v)
    """


def _get_kwargs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish_address', default=None)
    parser.add_argument('--prompt_name', default='vexbot')

    args = parser.parse_args()
    return vars(args)


def main(**kwargs):
    if not kwargs:
        kwargs = _get_kwargs()
    shell = Shell(**kwargs)
    cmd_loop_thread = Thread(target=shell.cmdloop)
    cmd_loop_thread.daemon = True
    cmd_loop_thread.start()

    shell.run()

if __name__ == '__main__':
    main()
