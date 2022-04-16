# TimeTray
TimeTray displays the current calendar week in a system tray


## Python version

To run the Python version, just create a shortcut to you python interpreter:
1. `python3 -m pip install -r requirements.txt`
1. `"F:\Python\pythonw.exe" "D:\User\timetray\TimeTray.py"`
1. https://stackoverflow.com/questions/9705982/pythonw-exe-or-python-exe

### Python volume mixing

![volume mixing](volumemixing.gif)


## How to build your own Jar file
Make your required edits to the TimeTray.java file.
Run the following commands to build the new jar file:
1. `rm -rf *.class *.jar`
1. `javac TimeTray.java`
1. `jar -cmf TimeTray.mf TimeTray.jar *.class`

Run the following commands to see the jar file contents:
1. `jar tf TimeTray.jar`

Run the following commands to execute the jar file contents:
1. `java -jar .\TimeTray.jar`


## How to add to windows startup
Go to:
1. `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
1. Create shortcup to starup here
1. `Shortcup target = "C:\Program Files\OpenJDK\jdk-13.0.1\bin\javaw.exe" -jar "C:\WeekNum\TimeTray.jar"`
1. `Place your new TimeTray.jar in C:\WeekNum\`


## Install/Usage

If you don't use the "Download ZIP" option but only want to download _TimeTray.jar_, **don't right-click it in the list (!) but left-click on it and get the "RAW" version**!

Just make sure that you're running a Java Runtime Environment (e. g. the [JRE from Oracle](http://www.java.com/en/download/ "Oracle")), and put _TimeTray.jar_ into your autostart folder, crontab, whatever...


## Screenshot
![timetray](https://github.com/otacke/timetray/blob/master/timetray.png "timetray")


## Additional Information
TimeTray is a very simple program that I originally hacked on one day for a former colleague of mine many years ago. It displays the current calender week in a system tray -- a feature that Windows still lacks in 2016. Since TimeTray is written in Java, it can run on other operating systems as well, e.g. Linux or MacOS.

TimeTray is totally working -- I hope ;-) I cannot test it on Windows because I don't use Windows. So, if you detect a problem, just tell me, please. Anyway, allowing to set (and save) some parameters would be useful:

* the tray icon's background color
* the tray icon's font color
* the tray icon's font
* an optional offset of -1 or +1 if you're running a locale version of your OS that doesn't match your local calendar customs

So far, there is a rudimental settings window that allows you to change the offset that is saved automatically to a plain text file called _.timetray_ in your home directory. You can edit the file with a text editor line by line to change other values. The lines mean...

1. (0-255) red value of the TrayIcon's background color
2. (0-255) green value of the TrayIcon's background color
3. (0-255) blue value of the TrayIcon's background color
4. (0-255) alpha value of the TrayIcon's background color
5. (0-255) red value of the font color
6. (0-255) green value of the font color
7. (0-255) blue value of the font color
8. (0-255) alpha value of the font color
9. (-1, 0, 1) time offset
10. name of the font family
11. number representing the font style (I didn't look up which number means what, but 0 is plain)
12. simple date format pattern representing the format for the TrayIcons toolstip text

The load and save routines are only rudimentary, so you might crash TimeTray if you set illegal values. In doubt, delete .timetray in your home directory. TimeTray will then reset the file if neccessary. The ugly routines should probably be improved...

_When will all this be done? When it's done. But to be honest: I don't care much about this piece of code that's probably mainly used for Windows. Sorry! But you may use the source, Luke!_

