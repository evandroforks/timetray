#!/bin/bash

# Print 
echo Creating new tar file and executing...Look in your system tray in the bottom right

rm -rf *.class *.jar
javac TimeTray.java
jar -cmf TimeTray.mf TimeTray.jar *.class
javaw -jar TimeTray.jar
