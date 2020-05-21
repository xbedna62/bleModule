cp bleModule.py /myapp/iot/bleModule.py

cp bleModule.service /etc/systemd/system
systemctl daemon-reload
systemctl enable bleModule.service
systemctl start bleModule.service
