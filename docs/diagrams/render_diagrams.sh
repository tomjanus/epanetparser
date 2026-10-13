#!/usr/bin/env bash
#
# Regenerate the PlantUML diagrams used by the Sphinx documentation.
#
# The .puml sources live in ../source/diagrams, next to the .svg and .png files
# that Sphinx embeds. The PlantUML jar is vendored under tools/ so rendering
# does not depend on a system install; the only external requirement is a Java
# runtime (21 is known to work). Both SVG (used by Sphinx) and PNG (a raster
# copy for readers) are produced. Run it with the docs Makefile:
#
#   make diagrams
#
# or directly:
#
#   ./render_diagrams.sh
#
# Set the JAVA environment variable to use a specific Java executable, e.g.
#   JAVA=/usr/lib/jvm/java-21-openjdk/bin/java ./render_diagrams.sh
set -euo pipefail

# Directory containing this script, resolved so the script works from anywhere.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Sphinx reads the generated images from docs/source/diagrams.
DIAGRAM_DIR="${DIAGRAM_DIR:-${SCRIPT_DIR}/../source/diagrams}"
PLANTUML_JAR="${SCRIPT_DIR}/tools/plantuml.jar"
JAVA="${JAVA:-java}"

if [[ ! -f "${PLANTUML_JAR}" ]]; then
    echo "error: PlantUML jar not found at ${PLANTUML_JAR}" >&2
    exit 1
fi

if ! command -v "${JAVA}" >/dev/null 2>&1; then
    echo "error: Java executable '${JAVA}' not found; set JAVA to override" >&2
    exit 1
fi

shopt -s nullglob
diagrams=("${DIAGRAM_DIR}"/*.puml)
shopt -u nullglob

if [[ ${#diagrams[@]} -eq 0 ]]; then
    echo "error: no .puml files found in ${DIAGRAM_DIR}" >&2
    exit 1
fi

for puml in "${diagrams[@]}"; do
    for format in svg png; do
        echo "Rendering $(basename "${puml}") -> ${format}"
        "${JAVA}" -Djava.awt.headless=true -jar "${PLANTUML_JAR}" \
            "-t${format}" -o "${DIAGRAM_DIR}" "${puml}"
    done
done

echo "Rendered ${#diagrams[@]} diagram(s) to ${DIAGRAM_DIR}"
