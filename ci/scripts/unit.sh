#!/bin/bash -eux

pushd dp-conceptual-search
  make build test && make clean
popd
