# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for genro_core."""

import _thread
import uuid
import base64


def getUuid():
    """
    Return a Python Universally Unique IDentifier 3 (UUID3).

    This function generates a URL-safe UUID by:
    1. Getting the current thread ID
    2. Creating a UUID3 from UUID1 + thread ID
    3. Base64 URL-safe encoding
    4. Taking first 22 characters
    5. Replacing '-' with '_' for better URL compatibility

    Returns:
        str: A 22-character URL-safe unique identifier

    Example:
        >>> uuid_str = getUuid()
        >>> len(uuid_str)
        22
        >>> '_' in uuid_str or '-' in uuid_str
        True
    """
    t_id = _thread.get_ident()
    t_id = str(t_id)
    uuid_to_encode = uuid.uuid3(uuid.uuid1(), t_id).bytes
    return base64.urlsafe_b64encode(uuid_to_encode)[0:22].replace(b'-', b'_').decode()
