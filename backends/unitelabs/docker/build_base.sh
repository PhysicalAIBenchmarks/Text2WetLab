#!/bin/bash
# Build the base image for the UniteLabs tasks.
#
#     docker/build_base.sh <liquid-handling SDK checkout> <unitelabs-sdk checkout | -> <unitelabs-labware checkout | -> <docs checkout>
#
# Builds the liquid-handling SDK wheel from its checkout, exports its uv.lock as pip constraints, stages the docs
# content from the docs repo's `main` (whatever branch the checkout is on), and builds
# docker/Dockerfile.base with ~/.netrc as a build secret (so pip can read the UniteLabs package index; the secret is
# never written into an image layer). unitelabs-sdk (Audit and the lineage contract) and unitelabs-labware (the model
# notifications the lineage loads and seeds come from) are built from their checkouts too, replacing the versions
# uv.lock pins, while the lineage work is unreleased; `-` installs the locked version from the index instead. The
# checkouts must be clean: the tag names their commits.
# Prints the image tag; tasks/*/environment/Dockerfile FROM it. The tag names the SDK and docs commits and a hash of
# the image recipe, so a run's result.json can say exactly what the agent was writing against.
set -euo pipefail
sdk="${1:?liquid-handling SDK checkout}"
ulsdk="${2:?unitelabs-sdk checkout, or - for the locked version}"
lw="${3:?unitelabs-labware checkout, or - for the locked version}"
docs="${4:?docs checkout}"
here="$(cd "$(dirname "$0")" && pwd)"
ctx="$here/.context"

pyproject_version() { grep -E '^version = ' "$1/pyproject.toml" | head -1 | sed -E 's/version = "(.*)"/\1/'; }
locked() { (cd "$sdk" && uv export --frozen --no-hashes --no-dev --no-emit-project | sed -nE "s/^$1==(.*)\$/\1/p"); }

sdk_commit="$(git -C "$sdk" rev-parse --short HEAD)"
docs_commit="$(git -C "$docs" rev-parse --short main)"
for checkout in "$sdk" "$ulsdk" "$lw"; do
    if [ "$checkout" != - ] && [ -n "$(git -C "$checkout" status --porcelain --untracked-files=no)" ]; then
        echo "refusing: $checkout has uncommitted changes" >&2; exit 1
    fi
done
version="$(pyproject_version "$sdk")"
if [ "$ulsdk" = - ]; then
    ulsdk_version="$(locked unitelabs-sdk)"; ulsdk_commit=index
else
    ulsdk_version="$(pyproject_version "$ulsdk")"; ulsdk_commit="$(git -C "$ulsdk" rev-parse --short HEAD)"
fi
if [ "$lw" = - ]; then
    labware="$(locked unitelabs-labware)"; labware_commit=index
else
    labware="$(pyproject_version "$lw")"; labware_commit="$(git -C "$lw" rev-parse --short HEAD)"
fi
pydantic="$(locked pydantic)"
# The recipe hash changes the tag whenever the Dockerfile or the files baked in from this repo change.
recipe="$(cat "$here/Dockerfile.base" "$here/simulate" "$here"/../ul/{runner,record,lineage_events,devices}.py | shasum -a 256 | cut -c1-8)"
tag="text2wetlab-ul-base:sdk${version}-${sdk_commit}-ulsdk${ulsdk_version}-${ulsdk_commit}-lw${labware}-${labware_commit}-docs${docs_commit}-r${recipe}"

rm -rf "$ctx"; mkdir -p "$ctx/wheels" "$ctx/docs"
# local_wheel <checkout> <dist file prefix>: build the checkout's wheel into the context, print its file name.
local_wheel() {
    (cd "$1" && uv build --wheel --out-dir "$ctx/wheels/$2" >/dev/null)
    mv "$ctx/wheels/$2"/*.whl "$ctx/wheels/"; rm -rf "${ctx:?}/wheels/$2"
    basename "$(ls "$ctx"/wheels/"$2"-*.whl)"
}
wheel="$(local_wheel "$sdk" unitelabs_liquid_handling)"
# *_spec is what the image installs (wheels sit in /tmp/wheels there), *_req what uv resolves here.
drop='^(-e |\.|file:'
if [ "$ulsdk" = - ]; then
    ulsdk_spec="unitelabs-sdk[automate]==${ulsdk_version}"; ulsdk_req="$ulsdk_spec"
else
    ulsdk_wheel="$(local_wheel "$ulsdk" unitelabs_sdk)"
    ulsdk_spec="/tmp/wheels/${ulsdk_wheel}[automate]"; ulsdk_req="$ctx/wheels/${ulsdk_wheel}[automate]"
    drop="$drop|unitelabs-sdk=="                  # the local wheel replaces the locked version
fi
if [ "$lw" = - ]; then
    labware_spec="unitelabs-labware==${labware}"; labware_req="$labware_spec"
else
    labware_wheel="$(local_wheel "$lw" unitelabs_labware)"
    labware_spec="/tmp/wheels/${labware_wheel}"; labware_req="$ctx/wheels/${labware_wheel}"
    drop="$drop|unitelabs-labware=="
fi
drop="$drop)"
(cd "$sdk" && uv export --frozen --no-hashes --no-dev --no-emit-project) | grep -vE "$drop" > "$ctx/constraints.txt"
if [ "$ulsdk" != - ] || [ "$lw" != - ]; then
    # A local wheel may need newer dependencies than the liquid-handling SDK's lock pins for the released one. Resolve the wheels
    # together for the image's Python, keeping that lock's versions wherever they still fit (uv pip compile
    # prefers the pins already in its output file). Run in the liquid-handling SDK checkout, so uv uses its index settings (the
    # UniteLabs index first, authenticated from ~/.netrc).
    printf '%s\n' "$ctx/wheels/$wheel" "$ulsdk_req" "$labware_req" > "$ctx/requirements.in"
    (cd "$sdk" && uv pip compile --quiet --python-version 3.13 --no-header --no-annotate \
        "$ctx/requirements.in" -o "$ctx/constraints.txt")
    grep -vE '^(/|-e |\.|file:)|^unitelabs-(liquid-handling|sdk|labware) @' "$ctx/constraints.txt" > "$ctx/c.txt"
    mv "$ctx/c.txt" "$ctx/constraints.txt"; rm "$ctx/requirements.in"
fi
git -C "$docs" archive main content | tar -x -C "$ctx/docs"
cp "$here"/../ul/{runner,record,lineage_events,devices}.py "$here/simulate" "$ctx/"
cp "$here/Dockerfile.base" "$ctx/Dockerfile"

DOCKER_BUILDKIT=1 docker build \
    --secret id=netrc,src="$HOME/.netrc" \
    --build-arg SDK_WHEEL="$wheel" --build-arg LABWARE_SPEC="$labware_spec" --build-arg ULSDK_SPEC="$ulsdk_spec" \
    --build-arg PYDANTIC_VERSION="$pydantic" \
    --build-arg SDK_COMMIT="$sdk_commit" --build-arg ULSDK_COMMIT="$ulsdk_commit" --build-arg LABWARE_COMMIT="$labware_commit" --build-arg DOCS_COMMIT="$docs_commit" \
    -t "$tag" -t text2wetlab-ul-base:latest "$ctx" >&2
rm -rf "$ctx"
echo "$tag"
