import json
import os
from flask import Blueprint
from flask import render_template
from flask import request
from logzero import logger
from solox.public.common import Devices, File, Method, CHART_DEFAULT_MAX_POINTS

page = Blueprint("page", __name__)
d = Devices()
m = Method()
f = File()


def _report_scene_exists(report_dir, scene):
    if (
        not scene
        or scene in ('.', '..')
        or '/' in scene
        or '\\' in scene
        or ':' in scene
        or os.path.isabs(scene)
        or os.path.basename(scene) != scene
    ):
        return False
    report_root = os.path.realpath(report_dir)
    scene_path = os.path.realpath(os.path.join(report_root, scene))
    if scene_path == report_root:
        return False
    try:
        if os.path.commonpath((report_root, scene_path)) != report_root:
            return False
    except ValueError:
        return False
    return os.path.isdir(scene_path)


def _report_result_exists(report_dir, scene):
    if not _report_scene_exists(report_dir, scene):
        return False
    return os.path.isfile(os.path.join(report_dir, scene, 'result.json'))


@page.app_errorhandler(404)
def page_404(e):
    settings = m._settings(request)
    return render_template('404.html', **locals()), 404

@page.app_errorhandler(500)
def page_500(e):
    settings = m._settings(request)
    return render_template('500.html', **locals()), 500

@page.route('/')
def index():
    platform = request.args.get('platform')
    lan = request.args.get('lan')
    settings = m._settings(request)
    return render_template('index.html', **locals())

@page.route('/pk')
def pk():
    lan = request.args.get('lan')
    model = request.args.get('model')
    settings = m._settings(request)
    return render_template('pk.html', **locals())

@page.route('/report')
def report():
    lan = request.args.get('lan')
    settings = m._settings(request)
    return render_template('report.html', **locals())

@page.route('/analysis', methods=['post', 'get'])
def analysis():
    lan = request.args.get('lan')
    scene = request.args.get('scene')
    app = request.args.get('app')
    platform = request.args.get('platform')
    settings = m._settings(request)
    report_dir = os.path.join(os.getcwd(), 'report')
    scene_exists = _report_scene_exists(report_dir, scene)
    scene_ready = _report_result_exists(report_dir, scene)
    filter_dir = []
    if scene_exists:
        try:
            filter_dir = f.filter_secen(scene)
        except (OSError, ValueError) as e:
            logger.warning('report list changed during analysis: %s', e)
    apm_data = {}
    scene_display = scene
    initial_disk = []
    current_disk = []
    sum_init_disk = {'sum_size': 0, 'sum_used': 0, 'sum_free': 0}
    sum_current_disk = {'sum_size': 0, 'sum_used': 0, 'sum_free': 0}
    if scene_ready:
        try:
            if platform == 'Android':
                apm_data = f._setAndroidPerfs(scene)
                disk = f.analysisDisk(scene)
                initial_disk = disk[0]
                current_disk = disk[1]
                sum_init_disk = disk[2]
                sum_current_disk = disk[3]
            else:
                apm_data = f._setiOSPerfs(scene)
            scene_display = apm_data.get('duration_label') or scene
        except ZeroDivisionError:
            pass
        except (OSError, ValueError) as e:
            logger.warning('report summary unavailable during analysis: %s', e)
        except Exception as e:
            logger.exception(e)
    return render_template('analysis.html', **locals(), chart_max_points=CHART_DEFAULT_MAX_POINTS)

@page.route('/pk_analysis', methods=['post', 'get'])
def analysis_pk():
    lan = request.args.get('lan')
    scene = request.args.get('scene')
    app = request.args.get('app')
    model = request.args.get('model')
    settings = m._settings(request)
    report_dir = os.path.join(os.getcwd(), 'report')
    apm_data = {}
    if _report_result_exists(report_dir, scene):
        try:
            apm_data = f._setpkPerfs(scene)
        except (OSError, ValueError) as e:
            logger.warning('pk report summary unavailable: %s', e)
        except Exception as e:
            logger.exception(e)
    return render_template(
        'analysis_pk.html',
        **locals(),
        chart_max_points=CHART_DEFAULT_MAX_POINTS,
    )

@page.route('/compare_analysis', methods=['post', 'get'])
def analysis_compare():
    platform = request.args.get('platform')
    lan = request.args.get('lan')
    scene1 = request.args.get('scene1')
    scene2 = request.args.get('scene2')
    app = request.args.get('app')
    settings = m._settings(request)
    report_dir = os.path.join(os.getcwd(), 'report')
    apm_data1 = {}
    apm_data2 = {}
    try:
        if (
            _report_result_exists(report_dir, scene1)
            and _report_result_exists(report_dir, scene2)
        ):
            if platform == 'Android':
                apm_data1 = f._setAndroidPerfs(scene1)
                apm_data2 = f._setAndroidPerfs(scene2)
            elif platform == 'iOS':
                apm_data1 = f._setiOSPerfs(scene1)
                apm_data2 = f._setiOSPerfs(scene2)
    except ZeroDivisionError:
        pass 
    except (OSError, ValueError) as e:
        logger.warning('compare report summary unavailable: %s', e)
    except Exception as e:
        logger.exception(e)          
    return render_template(
        'analysis_compare.html',
        **locals(),
        chart_max_points=CHART_DEFAULT_MAX_POINTS,
    )
