#!/bin/bash

taskset -c 15 stress-ng --cpu 1 --cpu-method ackermann --timeout 120s --cpu-load 100