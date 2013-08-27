base:
  'role:ogreserver':
    - match: grain
    - ogreserver
  'role:ogreclient':
    - match: grain
    - ogreclient

  'env:dev':
    - match: grain
    - dev-user
    - dev-build
