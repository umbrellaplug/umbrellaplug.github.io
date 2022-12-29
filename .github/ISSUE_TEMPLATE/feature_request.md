name: Feature Request
description: Create a request for a new feature.
title: "[FEATURE] Short Description"
labels: feature
body:
- type: textarea
  attributes:
    label: Feature
    description: A clear and concise description of what you're wanting added or changed.
  validations:
    required: true
- type: textarea
  attributes:
    label: Is this feature available already in another plugin?
    description: Information for if this feature already exists.
  validations:
    required: false