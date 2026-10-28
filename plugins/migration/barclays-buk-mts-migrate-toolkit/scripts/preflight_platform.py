"""Pre-flight Step 0.1 — Detect platform, Gradle wrapper, and Python command."""
import platform, os

plat = platform.system()  # 'Darwin', 'Linux', 'Windows'
wrapper = 'gradlew.bat' if plat == 'Windows' else './gradlew'
python_cmd = 'python' if plat == 'Windows' else 'python3'
wrapper_exists = os.path.isfile(os.path.join(os.getcwd(), wrapper.lstrip('./')))

print(f'PLATFORM={plat}')
print(f'GRADLE_WRAPPER={wrapper}')
print(f'GRADLE_WRAPPER_EXISTS={wrapper_exists}')
print(f'PYTHON_CMD={python_cmd}')
