from flask_classy import FlaskView, route
from flask import render_template, redirect, url_for, request, jsonify, Response
from flask_login import login_required, current_user

from bson.objectid import ObjectId
from app.common.subscriber.entry import Device
from app.common.service.forms import UploadM3uForm
from app.common.utils.m3u_parser import M3uParser
from app.common.utils.utils import is_valid_http_url
from app.common.stream.entry import ProxyStream
from app.common.stream.forms import ProxyStreamForm
import app.common.constants as constants
from app import app
import json


# routes
class SubscriberView(FlaskView):
    route_base = "/subscriber"

    def default_logo_url(self):
        return url_for('static', filename='images/unknown_channel.png', _external=True)

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

    @login_required
    def my_channels(self):
        form = UploadM3uForm(type=constants.StreamType.PROXY)
        form.type.render_kw = {'disabled': 'disabled'}
        streams = []
        for stream in current_user.own_streams:
            streams.append(stream.to_dict())

        return render_template('subscriber/my_channels.html', form=form, streams=streams)

    @login_required
    @route('/upload_files', methods=['POST'])
    def upload_files(self):
        form = UploadM3uForm()
        form.type.validators = []
        if form.validate_on_submit():
            files = request.files.getlist("files")
            for file in files:
                m3u_parser = M3uParser()
                m3u_parser.load_content(file.read().decode('utf-8'))
                m3u_parser.parse()

                default_logo_path = self.default_logo_url()
                for file in m3u_parser.files:
                    stream = ProxyStream.make_stream(None)

                    input_url = file['link']
                    stream.output.urls[0].uri = input_url

                    stream.tvg_logo = default_logo_path

                    title = file['title']
                    if len(title) < constants.MAX_STREAM_NAME_LENGTH:
                        stream.name = title

                    tvg_id = file['tvg-id']
                    if len(tvg_id) < constants.MAX_STREAM_TVG_ID_LENGTH:
                        stream.tvg_id = tvg_id

                    tvg_name = file['tvg-name']
                    if len(tvg_name) < constants.MAX_STREAM_NAME_LENGTH:
                        stream.tvg_name = tvg_name

                    tvg_group = file['tvg-group']
                    if len(tvg_group) < constants.MAX_STREAM_GROUP_TITLE_LENGTH:
                        stream.group = tvg_group

                    tvg_logo = file['tvg-logo']
                    if len(tvg_logo) < constants.MAX_URL_LENGTH:
                        if is_valid_http_url(tvg_logo, timeout=0.1):
                            stream.tvg_logo = tvg_logo
                    stream.save()
                    current_user.add_own_stream(stream)

        return redirect(url_for('SubscriberView:my_channels'))

    @route('/remove_own_stream', methods=['POST'])
    @login_required
    def remove_own_stream(self):
        data = request.get_json()
        sids = data.get('sids', None)
        if not sids:
            return jsonify(status='failed', error='Invalid input(country required)'), 400

        for sid in sids:
            current_user.remove_own_stream(sid)
        return jsonify(status='ok'), 200

    @login_required
    def remove_all_own_streams(self):
        current_user.remove_all_own_streams()
        return jsonify(status='ok'), 200

    @login_required
    @route('/add/own/stream', methods=['GET', 'POST'])
    def add_own_stream(self):
        stream = ProxyStream.make_stream(None)
        form = ProxyStreamForm(obj=stream)
        form.price.validators = []
        if request.method == 'POST' and form.validate_on_submit():
            new_entry = form.make_entry()
            new_entry.save()
            current_user.add_own_stream(new_entry)
            return jsonify(status='ok'), 200

        return render_template('stream/proxy/add.html', form=form)

    @login_required
    @route('/edit/own/<sid>', methods=['GET', 'POST'])
    def edit(self, sid):
        stream = current_user.find_own_stream(sid)
        if not stream:
            return jsonify(status='failed'), 404

        form = ProxyStreamForm(obj=stream)
        form.price.validators = []
        if request.method == 'POST' and form.validate_on_submit():
            stream = form.update_entry(stream)
            stream.save()
            return jsonify(status='ok'), 200

        return render_template('stream/proxy/edit.html', form=form)

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
