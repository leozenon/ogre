# Solve the Chicken and egg problem where grains need to run before any
# of the modules are loaded and are generally available for any usage.
import salt.modules.cmdmod

__salt__ = {
    'cmd.run': salt.modules.cmdmod._run_quiet,
}


def is_vmware():
    grains = {}
    res = __salt__['cmd.run'](
        'ps -ef | grep -P "(vmware|vmtoolsd)" | grep -v grep'
    )
    if len(res) > 0:
        grains['vmware'] = True

    return grains
