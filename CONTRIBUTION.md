# Contribution Guidelines
## Welcome

## Contributing Code
If you'd like to contribute to our project pick an issue from the [Kanban](https://github.com/UoA-CARES/FastAnnotation/projects/1) that you like the look of. Be sure to assign yourself to any issues you are working on and move their status to 'In Progress' on the Kanban.

### Feature Branch Conventions
When making a feature branch to submit your code, branch off `develop`. The `master` branch is reserved for releases and should not branched from.

Additionally when naming your branch:
1. prefix the branch name with `feature/` or `fix/` if the issue pertains to a bug
1. keep the branch name in [snake_case](https://en.wikipedia.org/wiki/Snake_case)
1. keep the branch name short and simple

A good branch name might be `feature/create_annotations` or `fix/server_connection`.

### Code Style
To keep a consistent style through our code base, we will use the [PEP8](https://www.python.org/dev/peps/pep-0008/) coding standard. This can achieved automatically with [Autopep8](https://pypi.org/project/autopep8/) from the commandline or integrated into most IDEs.

### Pull Request Conventions
Before submitting a pull request, ensure that your code has met the Acceptance Critiera outlined in the issue. Make sure that you mention the issue number in your Pull Request by either "Resolves #X" or "Closes #X" to automatically link the appropriate issue.

