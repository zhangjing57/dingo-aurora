import json
from os import path
import shutil
from string import ascii_letters,digits
from random import sample
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
import ansible.constants as C

KEYS_SUCCESS = "success"
KEYS_FAILED = "failed"
KEYS_UNREACHABLE = "unreachable"
KEYS_SKIPPED = "skipped"
PLAYBOOK_DIR = "/playbook"


class PlaybookResultCallback(CallbackBase):
    """
    return data
    {
            "task_name1": {
                "success": {
                    "192.168.8.33": {
                        {"changed": "true", "end": "2019-01-17 02:31:58.519839", "stdout": "{}" ...}
                    },
                    "192.168.8.34": {

                    }
                },
                "failed": {
                    "192.168.8.35": {

                    }
                },
                "unreachable": {
                    "192.168.8.36": {

                    }
                },
                "skipped": {

                }
            }
        }
    """

    def __init__(self, *args, **kwargs):
        super(PlaybookResultCallback,self).__init__(*args, **kwargs)
        self.task_unreachable = []
        self.result = {}

    def __init_result_dict(self, result):
        if not result._task.name in self.result:
            self.result[result._task.name] = {
                KEYS_SUCCESS: {},
                KEYS_FAILED: {},
                KEYS_UNREACHABLE: {},
                KEYS_SKIPPED: {}
            }

    def __set_ansi_result(self, result, type):
        self.result[result._task.name][type][result._host] = result._result

    def __fix_unreachable_result(self, result):
        if self.task_unreachable:
            for task_unreachable in self.task_unreachable:
                unreachable_host = task_unreachable["host"]
                if not unreachable_host in self.result[result._task.name][KEYS_UNREACHABLE]:
                    self.result[result._task.name][KEYS_UNREACHABLE][unreachable_host] = task_unreachable["msg"]

    def v2_runner_on_unreachable(self, result, ignore_errors=True):
        print("unreachable task {} on host {}".format(result._task, result._host))
        task_unreachable = {
            "host": result._host,
            "msg": result._result
        }
        self.task_unreachable.append(task_unreachable)
        self.__init_result_dict(result)
        self.__set_ansi_result(result, KEYS_UNREACHABLE)
        #self.result[result._task.name][result._host] = result._result

    def v2_runner_on_ok(self, result, *args, **kwargs):
        print("playbook task {} ok on host {}".format(result._task, result._host))
        self.__init_result_dict(result)
        self.__set_ansi_result(result, KEYS_SUCCESS)
        self.__fix_unreachable_result(result)
        # self.result[result._task.name]["success"][result._host] = result._result
        ## add unreachable
        """if self.task_unreachable:
            for task_unreachable in self.task_unreachable:
                unreachable_host = task_unreachable["host"]
                if not unreachable_host in self.result[result._task.name]:
                    self.result[result._task.name][unreachable_host] = task_unreachable["msg"]"""

    def v2_runner_on_failed(self, result, ignore_errors=True, *args, **kwargs):
        print("failed task {} on host {}".format(result._task, result._host))
        self.__init_result_dict(result)
        self.__set_ansi_result(result, KEYS_FAILED)
        self.__fix_unreachable_result(result)

    def v2_runner_on_skipped(self, result, ignore_errors=True, *args, **kwargs):
        print("unreachable task {}  on host {}".format(result._task, result._host))
        self.__init_result_dict(result)
        self.__set_ansi_result(result, KEYS_SKIPPED)
        self.__fix_unreachable_result(result)


class CmdResultCallback(CallbackBase):
    def __init__(self, *args, **kwargs):
        super(CmdResultCallback,self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}
        self.host_skipped = {}

    def v2_runner_on_unreachable(self, result):
        print("unreachable task {task} on host {host}, result is {result}".format(
            task=result._task, host=result._host, result=json.dumps(result._result)))
        self.host_unreachable[result._host.get_name()] = result

    def v2_runner_on_ok(self, result, *args, **kwargs):
        self.host_ok[result._host.get_name()] = result

    def v2_runner_on_failed(self, result, *args, **kwargs):
        print("failed task {task} on host {host}, result is {result}".format(
            task=result._task, host=result._host, result=json.dumps(result._result)))
        self.host_failed[result._host.get_name()] = result

    def v2_runner_on_skipped(self, result, *args, **kwargs):
        print("skipped task {task} on host {host}, result is {result}".format(
            task=result._task, host=result._host, result=json.dumps(result._result)))
        self.host_skipped[result._host.get_name()] = result


class AnsibleApi(object):
    def __init__(self, inventory_path, default_ssh_username, default_ssh_password,
                 default_key_file, **kwargs):
        self.args = kwargs
        if "ansible_user" not in self.args:
            self.args["ansible_user"] = default_ssh_username
        self.ips = None
        self.inventory_path = inventory_path
        self.default_username = default_ssh_username
        self.default_password = default_ssh_password
        self.default_key_file = default_key_file
        self.loader = DataLoader()
        self.variable_manager = None
        self.options = None
        self.executor = None
        self.inventory = None
        self.password = {}
        self.cmd_callback = CmdResultCallback()
        self.play_callback = PlaybookResultCallback()
        self.init_executor()

    def __set_options(self):
        opts = ['listtags', 'listtasks', 'listhosts', 'syntax', 'connection',
                'module_path', 'forks', 'remote_user', 'private_key_file',
                'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
                'scp_extra_args', 'become', 'become_method', 'become_user',
                'verbosity', 'check', 'diff', 'basedir']
        Options = namedtuple('Options', opts)
        self.options = Options(
            listtags=False,
            listtasks=False,
            listhosts=False,
            syntax=False,
            connection='ssh',
            module_path=None,
            forks=100,
            remote_user=self.default_username,
            private_key_file=self.default_key_file,
            ssh_common_args="-o StrictHostKeyChecking=no",
            ssh_extra_args=None,
            sftp_extra_args=None,
            scp_extra_args=None,
            become=True,
            become_method='sudo',
            become_user='root',
            verbosity=self.args.get("verbosity", "3"),
            check=False,
            diff=False,
            basedir=PLAYBOOK_DIR
        )

    def __set_inventory(self):
        self.inventory = InventoryManager(loader=self.loader, sources=[self.inventory_path])

    def __set_default_password(self):
        if self.default_password:
            self.args["ansible_ssh_pass"] = self.default_password
            self.password = {"become_pass": self.default_password}

    def __set_variable_manager(self):
        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

    def __set_extra_vars(self):
        aaa = self.args.copy()
        self.variable_manager.extra_vars = aaa

    def set_extra_vars(self,vars):
        if not vars :
            self.variable_manager.extra_vars = self.variable_manager.extra_vars.update(vars)

    def get_extra_vars(self):
        return self.variable_manager.extra_vars

    # def __generate_inventory(self):
    #     file_name = ''.join(sample(ascii_letters + digits, 8))
    #     inventory_path = path.join(PROJECT_DIR, file_name)

    #     content = "[{}]\n".format(file_name)
    #     for ip in self.ips:
    #         content += ip
    #         if ip == "localhost":
    #             content += "\t ansible_connection=local"
    #         content += "\n"
    #     with open(inventory_path, "w") as f:
    #         f.write(content)
    #     return inventory_path

    def init_executor(self):
        #self.inventory_path = self.__generate_inventory()
        self.__set_inventory()
        self.__set_variable_manager()
        self.__set_options()
        self.__set_default_password()
        self.set_extra_vars(self.args)

    def run_ansible(self, task_list, host_ips=None):
        if host_ips is None:
            host_ips = self.ips
        file_name = ''.join(sample(ascii_letters + digits, 8))
        play_source = dict(
            name="Ansible Play {}".format(file_name),
            hosts=host_ips,
            gather_facts='no',
            tasks=task_list
        )
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.password,
                stdout_callback=self.cmd_callback,
                run_additional_callbacks=C.DEFAULT_LOAD_CALLBACK_PLUGINS,
                run_tree=False,
            )
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
            shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)
        return result

    def run_playbook(self, playbook_path, ip=None, **kwargs):
        #print('self_ips_run_playbook:',self.ips)
        # self.variable_manager.extra_vars = {'ansible_ssh_pass': self.default_password, 'disabled': 'yes'}
        #self.variable_manager.extra_vars = self.args
        playbook = PlaybookExecutor(playbooks=playbook_path,
                                    inventory=self.inventory,
                                    variable_manager=self.variable_manager,
                                    loader=self.loader,
                                    passwords=self.password)
        playbook._tqm._stdout_callback = self.play_callback

        return playbook.run()

    def get_cmd_result(self):

        results = {
            "success": {},
            "failed": {},
            "unreachable": {},
            "skipped": {}
        }

        for host, result in self.cmd_callback.host_ok.items():
            results['success'][host] = json.dumps(result._result)

        for host, result in self.cmd_callback.host_failed.items():
            print("failed task", result._result['stderr'] if 'stderr' in result._result else result._result['msg'])
            results['failed'][host] = result._result['stderr'] if 'stderr' in result._result else result._result['msg']

        for host, result in self.cmd_callback.host_unreachable.items():
            print("unreachable task", result._result['stderr'] if 'stderr' in result._result else result._result['msg'])
            results['unreachable'][host] = result._result['stderr'] if 'stderr' in result._result else result._result['msg']

        for host, result in self.cmd_callback.host_skipped.items():
            print("host_skipped task", result._result['stderr'] if 'stderr' in result._result else result._result['msg'])
            results['skipped'][host] = result._result['stderr'] if 'stderr' in result._result else result._result['msg']
        return results

    def get_playbook_result(self):
        return self.play_callback.result


def fn_collect3():
    host_list = ['192.168.8.33', '192.168.8.35']
    api = AnsibleApi(host_list, "root", "rootroot", "", )

    api.run_playbook(["/Users/liyongxin/PycharmProjects/alauda-trouble-shooting/playbook/diagnose.yml"])

    return api.get_playbook_result()

if __name__ == "__main__":
    res = fn_collect3
    print(json.dumps(res))