# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2023 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===
# }}}

'''VOLTTRON platform™ messaging classes.'''


import zmq
from volttron.platform import jsonapi

from .headers import Headers


__all__ = ['Socket']

__author__ = 'Brandon Carpenter <brandon.carpenter@pnnl.gov>'
__copyright__ = 'Copyright (c) 2016, Battelle Memorial Institute'
__license__ = 'Apache 2.0'


class Socket(zmq.Socket):
    '''ØMQ socket with additional agent messaging methods.'''

    def __new__(cls, socket_type, context=None):
        if not context:
            context = zmq.Context.instance()
        return zmq.Socket.__new__(cls, context, socket_type)

    def __init__(self, socket_type, context=None):
        super(Socket, self).__init__(self.context, socket_type)

    # Override send_string to ensure copy defaults to True.
    # https://github.com/zeromq/pyzmq/pull/456
    def send_string(self, u, flags=0, copy=True, encoding='utf-8'):
        super(Socket, self).send_string(
                u, flags=flags, copy=copy, encoding=encoding)
    send_string.__doc__ = zmq.Socket.send_string.__doc__

    def recv_message(self, flags=0):
        '''Recieve a message as (topic, headers, message) tuple.'''
        topic = self.recv_string(flags)
        headers = self.recv_string(flags) if self.rcvmore else ''
        headers = jsonapi.loads(headers) if headers else {}
        message = self.recv_multipart(flags) if self.rcvmore else []
        return topic, Headers(headers), message

    def recv_message_ex(self, flags=0):
        '''Receive a message as (content type, message) tuples.

        Like recv_message(), returns a three tuple.  However, the final
        message component contains a list of 2-tuples instead of a list
        of messages.  These 2-tuples contain the content- type and the
        data.
        '''
        topic, headers, message = self.recv_message(flags)
        message = list(zip(headers['Content-Type'], message))
        return topic, headers, message

    def send_message(self, topic, headers, *msg_parts, **kwargs):
        '''Send a multipart message with topic and headers.

        Send a multipart message on the socket with topic being a UTF-8
        string, headers can be a dictionary or a Headers object, and
        msg_parts is the optional parts of the message.  The media or
        content type of each message component should be included in the
        'Content-Type' header which should be a list of MIME types or a
        string if there is only one message part.
        '''
        flags = kwargs.pop('flags', 0)
        if kwargs:
            raise TypeError('send_message() got unexpected keyword '
                            'arugment(s): ' + ', '.join(kwargs))
        if not isinstance(headers, Headers):
            headers = Headers(headers) if headers else Headers()
        self.send_string(topic, flags | zmq.SNDMORE)
        self.send_json(headers.dict, flags | (zmq.SNDMORE if msg_parts else 0))
        if msg_parts:
            self.send_multipart(msg_parts, flags)

    def send_message_ex(self, topic, headers, *msg_tuples, **kwargs):
        '''Send messages given as (content-type, message) tuples.

        Similar to the send_message method except that messages are given as
        2-tuples with the MIME type as the first element and the message
        data as the second element.
        '''
        headers = Headers(headers) if headers else Headers()
        headers['Content-Type'], msg_parts = list(zip(*msg_tuples))
        self.send_message(topic, headers.dict, *msg_parts, **kwargs)
