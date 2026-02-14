oimport sys
from jinja2 import TemplateSyntaxError
import os

# Import the Flask app so we use the same Jinja environment and registered filters
try:
    from app import app
except Exception as e:
    print('ERROR importing app:', e)
    sys.exit(1)

try:
    names = app.jinja_env.list_templates()
except Exception as e:
    print('ERROR listing templates from Flask app:', e)
    sys.exit(1)

print('Found templates:', len(names))
problem = None
for name in names:
    try:
        print('Checking', name)
        app.jinja_env.get_template(name)
    except TemplateSyntaxError as e:
        print('TemplateSyntaxError in', name)
        print(e)
        problem = (name, str(e))
        break
    except Exception as e:
        print('Other error loading', name, e)

if not problem:
    print('No template syntax errors detected.')
else:
    print('Problematic template:', problem)
