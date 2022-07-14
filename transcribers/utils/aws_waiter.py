import botocore

from enum import Enum


class WaitState(Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'


class CustomWaiter:
    def __init__(self, name, operation, argument, acceptors, client, delay=10, max_tries=60, matcher='path'):
        self.name = name
        self.operation = operation
        self.argument = argument
        self.client = client
        self.waiter_model = botocore.waiter.WaiterModel({
            'version': 2,
            'waiters': {
                name: {
                    "delay": delay,
                    "operation": operation,
                    "maxAttempts": max_tries,
                    "acceptors": [{
                        "state": state.value,
                        "matcher": matcher,
                        "argument": argument,
                        "expected": expected
                    } for expected, state in acceptors.items()]
                }}})
        self.waiter = botocore.waiter.create_waiter_with_client(self.name, self.waiter_model, self.client)

    def __call__(self, parsed, **kwargs):
        status = parsed
        if status is None:
            return

        for key in self.argument.split('.'):
            if not status:
                return
            elif key.endswith('[]'):
                status = status.get(key[:-2])[0]
            else:
                status = status.get(key)

    def _wait(self, **kwargs):
        event_name = f'after-call.{self.client.meta.service_model.service_name}'
        self.client.meta.events.register(event_name, self)
        self.waiter.wait(**kwargs)
        self.client.meta.events.unregister(event_name, self)


class TranscribeCompleteWaiter(CustomWaiter):
    def __init__(self, client, timeout=10 * 60):
        delay = 5
        max_tries = timeout // delay
        super().__init__(
            'TranscribeComplete', 'GetTranscriptionJob',
            'TranscriptionJob.TranscriptionJobStatus',
            {'COMPLETED': WaitState.SUCCESS, 'FAILED': WaitState.FAILURE},
            client, delay, max_tries
        )

    def wait(self, job_name):
        self._wait(TranscriptionJobName=job_name)
