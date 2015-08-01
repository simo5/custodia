Custodia API
============

Custodia uses a RESTful interface to give access to secrets.
Authentication and authorization are fully pluggable and are
therefore, not standardized.

Access paths are also not standardized, although the common practice
is to mount th secrets api under the /secrets URI

The Custodia API uses JSON to format requests and replies.

Key/Request formats
===================

A key is a dictionary that contains the 'type' and 'value' of a key.
Currently only the Simple type is recognized


Simple
------

Format:
 { type: "simple", value: <arbitrary> }

The Simple type is an arbitrary value holder. It is recommend but not
required to base64 encode binary values or non-string values.

The value must be representable as a valid JSON string. Keys are
validated before being stored, unknown key types or invalid JSON values
are refused and an error is returned.


Key Exchange Message
--------------------

the Key Exchange Message format builds on the JSON Web Signature and the
JSON Web Encryption specification to build respectively the request and
reply messages.
The aim is to provide the Custodia server the means to encrypt the reply
to a client that proves possession of private key.

Format:
- Query arguments for GET:
    type=kem
    value=Message
- JSON Value for PUT/GET Reply:
    {"type:"kem","value":"Message"}

 The Message for a GET is a JWT (JWS):
 (flattened/decoded here for clarity)
  { "protected": { "kid": <public-key-dentifier>,
                   "alg": "a valid alg name"},
    "claims": { "sub": <name-of-secret>,
                "exp": <unix-timestamp indicating expiration time>,
                ["value": <arbitrary> ]},
    "signature": "XYZ...." }

 Attributes:
 - public-key-identifier: This is the kid of a key that must be known to the
 Custodia service. If opportunistic encription is desired, and the requesting
 client is authenticated in other ways a "jku"  header could be used instead,
 and a key fetched on the fly. This is not recommended for the gneral case and
 is not currently supported by the implementation.
 - name-of-secret: this repeates the name of the secret embedded in the GET,
 This is used to prevent substitution attacks where a client is intercepted
 and its signed request is reused to request a different key.
 - unix-timestamp: used to limit replay attacks, indicated expiration time,
 and should be no further than 5 minutes in the future, with leway up to 10
 minutes to account for clock skews
 Additional claims may be present, for example a 'value'.

 The Message for a GET reply or a PUT is a JWS Encoded message (see above)
 nested in a JWE Encoded message:
 (flattened/decoded here for clarity):
  { "protected": { "kid": <public-key-dentifier>,
                   "alg": "a valid alg name",
                   "enc": "a valid enc type"},
    "encrypted_key": <JWE_Encrypted_Key>,
    "iv": <Initialization Vector>,
    "ciphertext": <Encrypted Content>,
    "tag": <Authentication Tag> }

 Attributes:
 - public-key-identifier: Must be the server public key identifier.
   reply (see above). Or the server public key for a PUT.
 - The inner JWS payload will typically contain a 'value' that is
   an arbitrary key.
   example: { type: "simple", value: <arbitrary> }


REST API
========

Objects
-------

There are essentially 2 objects recognized by the API:
- keys
- key containers

Key containers can be nested and named arbitrarily, however depending on
authorization schemes used the basic container is often named after a group or
a user in order to make authorization chcks simpler.


Getting keys
------------

A GET operation with the name of the key:
GET /secrets/name/of/key

A query parameter named 'type' can be provided, in that case the key is
returned only if it matches the requested type.

Returns:
- 200 and a JSON formatted key in case of success.
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 if no key was found
- 406 not acceptable, key type unknown/not permitted


Storing keys
------------

A PUT operation withthe name of the key:
PUT /secrets/name/of/key

The Content-Type MUST be 'application/json'
The Content-Length MUST be specified, and the body MUST be
a key in one of the valid formats described above.

Returns:
- 201 in case of success.
- 400 if the request format is invalid
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 one of the elements of the path is not a valid container
- 405 if the target is a directory instead of a key (path ends in '/')
- 406 not acceptable, key type unknown/not permitted
- 409 if the key already exists


Deleting keys
-------------

A DELETE operation with the name of the key:
DELETE /secrets/name/of/key

Returns:
- 204 in case of success.
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 if no key was found


Listing containers
------------------

A GET operation on a path that ends in a '/' translates into
a listing for a container.
A 'filter' query argument may be provided to filter on key/container
names within the container being listed.
GET /secrets/container/?filter=red

Implementations may assume a default container if none is excplicitly
provided: GET /secrets/ may return only keys under /<user-default>/*

Returns:
- 200 in case of success and a dictionary containing a list of all keys
  in the container and all subcontainers.
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 if no key was found


Creating containers
-------------------

A POST operation on a path will create a container with that name.
A trailing '/' is required
POST /secrets/mycontainer/

Default containers may be automatically created by an implementation.

Returns:
- 201 in case of success.
- 400 if the request format is invalid
- 401 if authentication is necessary
- 403 if access to the key is forbidden
- 404 one of the elements of the path is not a valid container
- 409 if the container already exsts


Deleting containers
-------------------

A DELETE operation with the name of the container:
DELETE /secrets/mycontainer/

Returns:
- 204 in case of success.
- 401 if authentication is necessary
- 403 if access to the container is forbidden
- 404 if no container was found
- 409 if the container is not empty