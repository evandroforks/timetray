@echo off

echo Creating new tar file and executing...Look in your system tray in the bottom right
del *.class *.jar /f
javac TimeTray.java
jar -cmf TimeTray.mf TimeTray.jar *.class
javaw -jar TimeTray.jar