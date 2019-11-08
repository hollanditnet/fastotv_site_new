from flask_classy import FlaskView, route
from flask import render_template, redirect, url_for, request, Response
from flask_login import login_required, current_user

from bson.objectid import ObjectId
from app.common.subscriber.entry import Device
from app import app
import json


# routes
class SubscriberView(FlaskView):
    route_base = "/subscriber"

    @login_required
    def profile(self):
        return render_template('subscriber/profile.html')

    @login_required
    def channels(self):
        streams = []
        for serv in current_user.servers:
            for stream in serv.streams:
                if stream.visible:
                    streams.append(stream.to_dict())

        selected_streams = []
        for stream in current_user.streams:
            selected_streams.append(str(stream.id))
        return render_template('subscriber/channels.html', streams=streams, selected_streams=selected_streams)

    @route('/apply_channels', methods=['POST'])
    @login_required
    def apply_channels(self):
        current_user.streams = []
        json_str = request.form['apply_channels_official_ids']
        if json_str:
            for sid in json.loads(json_str):
                current_user.streams.append(ObjectId(sid))
        current_user.save()
        return redirect(url_for('SubscriberView:channels'))

    @login_required
    def devices(self):
        return render_template('subscriber/devices.html')

    @login_required
    def downloads(self):
        return render_template('subscriber/downloads.html',
                               name=app.config['PUBLIC_CONFIG']['player']['name'],
                               name_lowercase=app.config['PUBLIC_CONFIG']['player']['name_lowercase'],
                               version=app.config['PUBLIC_CONFIG']['player']['version'])

    @route('/add_device', methods=['POST'])
    @login_required
    def add_device(self):
        device = Device(name=request.form['name'])
        current_user.add_device(device)
        return render_template('subscriber/devices.html')

    @route('/remove_device/<did>', methods=['POST'])
    @login_required
    def remove_device(self, did):
        current_user.remove_device(did)
        return render_template('subscriber/devices.html')

    @login_required
    @route('/playlist/<did>/master.m3u', methods=['GET'])
    def playlist(self, did):
        lb_server_host_and_port = app.config['SUBSCRIBERS_PORTAL_HTTP_SERVER']
        playlist = current_user.generate_playlist(did, lb_server_host_and_port)
        return Response(playlist, mimetype='application/x-mpequrl'), 200

    @login_required
    def build_installer_request(self):
        return render_template('subscriber/profile.html')

    @login_required
    def logout(self):
        current_user.logout()
        return redirect(url_for('HomeView:index'))

    @login_required
    def remove(self):
        current_user.delete()
        return redirect(url_for('HomeView:index'))
