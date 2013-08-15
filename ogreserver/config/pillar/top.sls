base:
  'role:ogreserver':
    - match: grain
    - ogreserver
  'role:ogreclient':
    - match: grain
    - ogreclient

  'env:dev':
    - match: grain
    - dev_vars

  '*':
    - github_pky
