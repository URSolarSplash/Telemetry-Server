# Set up the error handling and cleanup
function error_handler() {
  echo "[Telemetry Server Bundle] Error occurred on line ${1} while building bundle."
  echo "[Telemetry Server Bundle] Cleaning up - bundle not created!"
  rm -rf bundle-temp 2> /dev/null
  rm release-bundles/release-latest.zip 2> /dev/null
}

trap 'error_handler ${LINENO} $?' ERR

set -o errexit 2> /dev/null
set -o errtrace 2> /dev/null
#set -o errpipe 2> /dev/null
set -o nounset 2> /dev/null

echo "[Telemetry Server Bundle] Creating temporary directory..."
mkdir bundle-temp

echo "[Telemetry Server Bundle] Bundling python files..."
cp main.py bundle-temp/__main__.py
cp -R server bundle-temp/server

echo "[Telemetry Server Bundle] Zipping python files..."
cd bundle-temp
zip -r ../release-bundles/release-latest.zip *
cd ..

echo "[Telemetry Server Bundle] Building executable file..."
echo '#!/usr/bin/env python' | cat - release-bundles/release-latest.zip > release-bundles/release-latest
chmod u+x release-bundles/release-latest

echo "[Telemetry Server Bundle] Deleting temporary files..."
rm -rf bundle-temp 2> /dev/null
rm release-bundles/release-latest.zip 2> /dev/null
echo "[Telemetry Server Bundle] Bundle completed!"
