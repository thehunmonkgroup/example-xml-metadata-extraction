#!/usr/bin/env bash

# Wrapper script for lwe
# Starts lwe, setting LWE_CONFIG_DIR and LWE_DATA_DIR to the configuration and
# data directories for this package.

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

alias_config=$(alias lwe 2>/dev/null)
restore_alias() {
  eval "${alias_config}"
}
trap restore_alias EXIT
unalias lwe 2>/dev/null

LWE_CONFIG_DIR="${CURRENT_DIR}/example_xml_metadata_extraction/lwe/config" LWE_DATA_DIR="${CURRENT_DIR}/example_xml_metadata_extraction/lwe/data" lwe "$@"
