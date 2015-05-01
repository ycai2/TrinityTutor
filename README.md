Trinity Tutor
=========

by: Yisheng Cai - <i>Trinity College, CT</i><br>
    Peter Reheis - <i>Trinity College, CT</i><br>
    Steven Yee - <i>Trinity College, CT</i>

A prototype of the Trinity Tutor Application using Python3, hosted on Google App Engine cloud service. <br>

<b>Public Domain</b>: http://trinity-tutor.appspot.com<br>

<b>Functionality</b>: This blog allows any user to register for accounts, post blogs, and adding comments after each post. 

Google App Engine Launcher Run instructions: 
=============================================
1. To install Google App Engine SDK for Python, use the link below to start: https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python
2. For Mac-OS, there is a launcher application you could use to easily test and deploy our web app. 
3. After installing Google App Engine Launcher, you can run it.
4. To add project, click “+” sign at left bottom corner. 
5. Download Trinity Tutor from Github.
6. Choose Application Directory at .../TrinityTutor, and click Create.
7. You can now run the webapp locally with “RUN” button on the top bar. 
8. Redirect to localhost:11001 to start navigating your own Trinity Tutor. 


Deployment instructions: 
=======================================================================

9. To deploy the website on Internet, you need to log into your google account at: https://console.developers.google.com/project
10. Create a project with anyname.
11. Copy Project ID and paste it into first line of app.yaml (eg. Application: project_id)
12. Then click deploy button on Google App Engine Launcher
13. Redirect to http://project_id.appspot.com to start navigating Trinity Tutor. 

Terminal Run instructions:
===========================
1. First you must have Google App Engine installed.
2. cd into the Trinity Tutor folder.
3. Execute the following command: dev_appserver.py --enable_sendmail=yes app.yaml
	This will run Trinity Tutor on localhost:8000
	The administrative server will run on localhost:8080
4. If sendmail is not working properly, the confirmation emails will not be sent out and you will not be able to validate your account. If the email is sent, please ignore the confirmation link as it is configured to work for the deployed site which can be found at http://trinity-tutor.appspot.com . Proceed to Step 4.
5. However, you can “manually” validate your account after you register it by visiting localhost:8080. Select the user account from Datastore Viewer by listing User Entities. Copy the hashed email of the user account to your clipboard. Then enter localhost:8080/confirmation/ + the hashed email you just copied. Click on the button to verify the user account. This will verify the user account and give it full access to Trinity Tutor.


