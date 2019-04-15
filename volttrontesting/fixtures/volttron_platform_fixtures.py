import os
import pytest
from random import randint
import socket
import uuid

from volttrontesting.utils.platformwrapper import PlatformWrapper

PRINT_LOG_ON_SHUTDOWN = False


def print_log(volttron_home):
    if PRINT_LOG_ON_SHUTDOWN:
        if os.environ.get('PRINT_LOGS', PRINT_LOG_ON_SHUTDOWN):
            log_path = volttron_home + "/volttron.log"
            if os.path.exists(log_path):
                with open(volttron_home + "/volttron.log") as fin:
                    print(fin.read())
            else:
                print('NO LOG FILE AVAILABLE.')


def get_rand_ip_and_port():
    ip = "127.0.0.{}".format(randint(1, 254))
    port = get_rand_port(ip)
    return ip + ":{}".format(port)


def get_rand_port(ip=None):
    port = randint(5000, 6000)
    if ip:
        while is_port_open(ip, port):
            port = randint(5000, 6000)
    return port


def is_port_open(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((ip, port))
    return result == 0


def get_rand_vip():
    return "tcp://{}".format(get_rand_ip_and_port())


def get_rand_ipc_vip():
    return "ipc://@/" + str(uuid.uuid4())


def build_wrapper(vip_address, **kwargs):
    wrapper = PlatformWrapper(messagebus=kwargs.pop('message_bus', None),
                              ssl_auth=kwargs.pop('ssl_auth', False),
                              instance_name=kwargs.pop('instance_name', 'volttron_test'))
    print('BUILD_WRAPPER: {}'.format(vip_address))
    wrapper.startup_platform(vip_address=vip_address, instance_name='volttron_test',**kwargs)
    return wrapper


def cleanup_wrapper(wrapper):
    print('Shutting down instance: {0}, MESSAGE BUS: {1}'.format(wrapper.volttron_home, wrapper.message_bus))
    if wrapper.is_running():
        wrapper.remove_all_agents()
    # Shutdown handles case where the platform hasn't started.
    wrapper.shutdown_platform()
    wrapper.restore_conf()


def cleanup_wrappers(platforms):
    for p in platforms:
        cleanup_wrapper(p)


@pytest.fixture(scope="module",
                params=[('zmq', False), ('rmq', True)])
def volttron_instance_msgdebug(request):
    print("building msgdebug instance")
    wrapper = build_wrapper(get_rand_vip(),
                            msgdebug=True,
                            message_bus=request.param[0],
                            ssl_auth=request.param[1])

    def cleanup():
        cleanup_wrapper(wrapper)

    request.addfinalizer(cleanup)
    return wrapper


# IPC testing is removed since it is not used from VOLTTRON 6.0
@pytest.fixture(scope="function")
def volttron_instance_encrypt(request):
    print("building instance (using encryption)")

    address = get_rand_vip()
    wrapper = build_wrapper(address)

    def cleanup():
        cleanup_wrapper(wrapper)

    request.addfinalizer(cleanup)
    return wrapper


@pytest.fixture
def volttron_instance_web(request):
    print("building instance 1 (using web)")
    address = get_rand_vip()
    web_address = "http://{}".format(get_rand_ip_and_port())
    wrapper = build_wrapper(address,
                            bind_web_address=web_address)

    def cleanup():
        cleanup_wrapper(wrapper)

    request.addfinalizer(cleanup)
    return wrapper


@pytest.fixture(scope="module",
                params=[('zmq', False)])
def volttron_instance_module_web(request):
    print("building module instance (using web)")
    address = get_rand_vip()
    web_address = "http://{}".format(get_rand_ip_and_port())
    wrapper = build_wrapper(address,
                            bind_web_address=web_address,
                            message_bus=request.param[0],
                            ssl_auth=request.param[1])

    def cleanup():
        cleanup_wrapper(wrapper)

    request.addfinalizer(cleanup)
    return wrapper


# Generic fixtures. Ideally we want to use the below instead of
# Use this fixture when you want a single instance of volttron platform for
# test
@pytest.fixture(scope="module",
                params=[
                    ('zmq', False),
                    ('rmq', True)
                ])
def volttron_instance(request, **kwargs):
    """Fixture that returns a single instance of volttron platform for testing

    @param request: pytest request object
    @return: volttron platform instance
    """
    print("building instance")
    wrapper = None
    address = kwargs.pop("vip_address", get_rand_vip())
    wrapper = build_wrapper(address,
                            message_bus=request.param[0],
                            ssl_auth=request.param[1],
                            **kwargs)

    def cleanup():
        cleanup_wrapper(wrapper)

    request.addfinalizer(cleanup)
    return wrapper


# Use this fixture to get more than 1 volttron instance for test.
# Usage example:
# def test_function_that_uses_n_instances(request, get_volttron_instances):
#     instances = get_volttron_instances(3)
@pytest.fixture(scope="module")
def get_volttron_instances(request):
    """ Fixture to get more than 1 volttron instance for test
    Use this fixture to get more than 1 volttron instance for test. This
    returns a function object that should be called with number of instances
    as parameter to get a list of volttron instnaces. The fixture also
    takes care of shutting down all the instances at the end

    Example Usage:

    def test_function_that_uses_n_instances(get_volttron_instances):
        instance1, instance2, instance3 = get_volttron_instances(3)

    @param request: pytest request object
    @return: function that can used to get any number of
        volttron instances for testing.
    """
    all_instances = []

    def get_n_volttron_instances(n, should_start=True, **kwargs):
        get_n_volttron_instances.count = n
        instances = []
        for i in range(0, n):
            address = kwargs.pop("vip_address", get_rand_vip())
            wrapper = None
            if should_start:
                wrapper = build_wrapper(address, **kwargs)
            else:
                wrapper = PlatformWrapper()
            instances.append(wrapper)
        instances = instances if n > 1 else instances[0]
        # setattr(get_n_volttron_instances, 'instances', instances)
        get_n_volttron_instances.instances = instances
        return instances

    def cleanup():
        if isinstance(get_n_volttron_instances.instances, PlatformWrapper):
            print('Shutting down instance: {}'.format(
                get_n_volttron_instances.instances))
            cleanup_wrapper(get_n_volttron_instances.instances)
            return

        for i in range(0, get_n_volttron_instances.count):
            print('Shutting down instance: {}'.format(
                get_n_volttron_instances.instances[i].volttron_home))
            cleanup_wrapper(get_n_volttron_instances.instances[i])

    request.addfinalizer(cleanup)

    return get_n_volttron_instances


# Use this fixture when you want a single instance of volttron platform for zmq message bus
# test
@pytest.fixture(scope="module")
def volttron_instance_zmq(request):
    """Fixture that returns a single instance of volttron platform for testing

    @param request: pytest request object
    @return: volttron platform instance
    """
    wrapper = None
    address = get_rand_vip()

    wrapper = build_wrapper(address)

    def cleanup():
        print('Shutting down instance: {}'.format(wrapper.volttron_home))
        cleanup_wrapper(wrapper)

    request.addfinalizer(cleanup)
    return wrapper


# Use this fixture when you want a single instance of volttron platform for rmq message bus
# test
@pytest.fixture(scope="module")
def volttron_instance_rmq(request):
    """Fixture that returns a single instance of volttron platform for testing

    @param request: pytest request object
    @return: volttron platform instance
    """
    wrapper = None
    address = get_rand_vip()

    wrapper = build_wrapper(address,
                            message_bus='rmq',
                            ssl_auth=True)

    def cleanup():
        print('Shutting down RMQ instance: {}'.format(wrapper.volttron_home))
        cleanup_wrapper(wrapper)

    request.addfinalizer(cleanup)
    return wrapper
