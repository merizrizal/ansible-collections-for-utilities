#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025, Mei Rizal (merizrizal) <meriz.rizal@gmail.com>

# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
    name: custom_logging
    type: aggregate
    requirements:
      - enable in configuration
    short_description: Logging for Ansible playbook
    description:
      - This callback will write the Ansible playbook result into particular log file.
    options:
      log_directory:
        default: ./log
        description: The folder where log files will be created.
        type: str
        env:
          - name: ANSIBLE_LOG_DIRECTORY
        ini:
          - section: callback_custom_logging
            key: log_directory
'''

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from ansible.executor.stats import AggregateStats
from ansible.executor.task_result import TaskResult
from ansible.playbook import Playbook
from ansible.playbook.task import Task
from ansible.plugins.callback import CallbackBase
from ansible.utils.display import get_text_width
from ansible.utils.path import makedirs_safe


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'merizrizal.utils.custom_logging'

    LOG_FILE_SUFFIX = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    RECAP_FORMAT = '%(host)s : ok=%(ok)s  changed=%(changed)s  unreachable=%(unreachable)s  failed=%(failures)s  ' \
        'skipped=%(skipped)s  rescued=%(rescued)s  ignored=%(ignored)s'
    SEPARATOR = '=' * 150

    def __init__(self):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.path = ''
        self.playbook = ''
        self.start_time_now = datetime.now()
        self.start_time = self.start_time_now.strftime(self.TIME_FORMAT)

    def set_options(self, task_keys=None, var_options=None, direct=None):
        super().set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        self.log_directory = self.get_option('log_directory')

    def v2_runner_on_failed(self, result, ignore_errors=False):
        ignore_text = '.....ignoring' if ignore_errors else ''
        self._log(result, f'FAILED {ignore_text}')

    def v2_runner_on_ok(self, result: TaskResult):
        self._log(result, 'OK')

    def v2_runner_on_skipped(self, result: TaskResult):
        self._log(result, 'SKIPPED')

    def v2_runner_on_unreachable(self, result: TaskResult):
        self._log(result, 'UNREACHABLE')

    def v2_runner_on_async_failed(self, result: TaskResult):
        self._log(result, 'ASYNC_FAILED')

    def _log(self, result: TaskResult, category):
        data = json.dumps(result._result)
        if result._task.vars and result._task.vars.get('custom_logging_mask'):
            for mask in result._task.vars.get('custom_logging_mask'):
                data = re.sub(mask, '*********************************', data)

        self.logger.info(f'{self._write_text_with_tab(result._host.get_name(), 18)} => {category}')
        self.logger.info(f'{data} \r\n')

    def v2_playbook_on_task_start(self, task: Task, is_conditional):
        self.logger.info(f'BEGIN TASK [{task.get_name()}]')
        self.logger.info(self.SEPARATOR)

    def v2_playbook_on_start(self, playbook: Playbook):
        self.playbook = playbook._file_name
        self._make_log_file_path()

        self.logger.info(f'PLAYBOOK [{self.playbook}] \r\n')

    def _make_log_file_path(self):
        playbook_path = Path(self.playbook)

        log_subdirectory = Path(self.log_directory).joinpath(playbook_path.parent)
        makedirs_safe(log_subdirectory)

        self.path = log_subdirectory.joinpath(f'{playbook_path.stem}-{self.LOG_FILE_SUFFIX}.log')
        logging.basicConfig(filename=self.path,
                            encoding='utf-8',
                            datefmt=self.TIME_FORMAT,
                            format='%(asctime)s.%(msecs)03d | %(message)s',
                            level=logging.DEBUG)

    def v2_playbook_on_stats(self, stats: AggregateStats):
        play_recap_text = self._write_text_with_tab('PLAY RECAP ', 80, '*')
        play_recap_text = self._write_text_with_tab('', 70, '*') + play_recap_text

        self.logger.info(self.SEPARATOR)
        self.logger.info(play_recap_text)

        self._write_summary(stats)
        self._write_time_calculation()

    def _write_summary(self, stats: AggregateStats):
        hosts = sorted(stats.processed.keys())
        for host in hosts:
            summary = stats.summarize(host)

            msg = self.RECAP_FORMAT % {
                'host': self._write_text_with_tab(host, 20),
                'ok': self._write_text_with_tab(summary['ok'], 4),
                'changed': self._write_text_with_tab(summary['changed'], 4),
                'unreachable': self._write_text_with_tab(summary['unreachable'], 4),
                'failures': self._write_text_with_tab(summary['failures'], 4),
                'skipped': self._write_text_with_tab(summary['skipped'], 4),
                'rescued': self._write_text_with_tab(summary['rescued'], 4),
                'ignored': self._write_text_with_tab(summary['ignored'], 4),
            }

            self.logger.info(msg)

    def _write_time_calculation(self):
        end_time_now = datetime.now()
        end_time = end_time_now.strftime('%Y-%m-%d %H:%M:%S')

        start_text = 'Playbook was started'
        start_text = f'{self._write_text_with_tab(start_text, 20)} => {self.start_time}'
        finish_text = 'Playbook finished'
        finish_text = f'{self._write_text_with_tab(finish_text, 20)} => {end_time}'

        runtime = end_time_now - self.start_time_now
        hours = runtime.seconds // 3600
        minutes = (runtime.seconds // 60) % 60
        seconds = runtime.seconds % 60

        self.logger.info(start_text)
        self.logger.info(finish_text)
        self.logger.info(f'Playbook run took {hours} hours, {minutes} minutes, {seconds} seconds\n\r')

        self._display.banner(start_text)
        self._display.banner(finish_text)

    def _write_text_with_tab(self, text, width, char=' '):
        length = width - get_text_width(str(text))
        return f'{text}{char * length}'
