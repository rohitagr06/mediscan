"""Enable `python -m mediscan.ui` to launch the app.

A package's __main__.py is what runs when you execute the package with
`python -m`. We just delegate to ui.app.main().
"""

from mediscan.ui.app import main

if __name__ == "__main__":
    main()
