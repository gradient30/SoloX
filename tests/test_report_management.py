# -*- coding: utf-8 -*-
"""Report list duration labels and chart downsample."""

import json
import os
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from solox.public.common import File, Platform


class TestDurationLabel(unittest.TestCase):

    def test_format_duration_label(self):
        self.assertEqual(File.format_duration_label(332), 'apm_05:32')
        self.assertEqual(File.format_duration_label(3665), 'apm_01:01:05')
        self.assertEqual(File.format_duration_label(0), '')

    def test_persist_and_read_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = File()
            f.report_dir = tmp
            scene = 'apm_test'
            scene_dir = os.path.join(tmp, scene)
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                json.dump({'app': 'com.test', 'ctime': '2026-03-15-16-31-18'}, fh)
            with open(os.path.join(scene_dir, 'cpu_app.log'), 'w', encoding='utf-8') as fh:
                fh.write('10:00:00.000000=10\n10:05:32.000000=20\n')
            f.persist_report_duration(scene)
            meta = json.load(open(os.path.join(scene_dir, 'result.json'), encoding='utf-8'))
            self.assertEqual(meta['duration'], '05:32')
            self.assertEqual(meta['duration_label'], 'apm_05:32')
            self.assertEqual(meta['duration_seconds'], 332)


class TestChartDownsample(unittest.TestCase):

    def test_downsample_caps_points(self):
        f = File()
        data = [{'x': str(i), 'y': i} for i in range(10000)]
        out = f._downsample_chart(data, 1500)
        self.assertEqual(len(out), 1500)
        self.assertEqual(out[-1]['y'], 9999)

    def test_readlog_downsample(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = File()
            f.report_dir = tmp
            scene = 'apm_ds'
            os.makedirs(os.path.join(tmp, scene))
            with open(os.path.join(tmp, scene, 'fps.log'), 'w', encoding='utf-8') as fh:
                for i in range(5000):
                    fh.write(f'10:00:{i % 60:02d}.000000={i % 60}\n')
            chart, _ = f.readLog(scene, 'fps.log', max_points=100)
            self.assertEqual(len(chart), 100)

    def test_compare_and_pk_apis_cap_real_large_logs(self):
        from solox.view import apis
        from solox.web import app

        app.config['TESTING'] = True
        client = app.test_client()
        with tempfile.TemporaryDirectory() as tmp:
            for scene in ('apm_first', 'apm_second', 'apm_pk'):
                os.makedirs(os.path.join(tmp, scene))
            for scene in ('apm_first', 'apm_second'):
                with open(
                    os.path.join(tmp, scene, 'cpu_app.log'),
                    'w',
                    encoding='utf-8',
                ) as fh:
                    for index in range(5000):
                        fh.write('10:00:{:02d}.000000={}\n'.format(
                            index % 60,
                            index,
                        ))
            for filename in ('cpu_app1.log', 'cpu_app2.log'):
                with open(
                    os.path.join(tmp, 'apm_pk', filename),
                    'w',
                    encoding='utf-8',
                ) as fh:
                    for index in range(5000):
                        fh.write('10:00:{:02d}.000000={}\n'.format(
                            index % 60,
                            index,
                        ))

            with patch.object(apis.f, 'report_dir', tmp):
                compare = client.get('/apm/log/compare', query_string={
                    'scene1': 'apm_first',
                    'scene2': 'apm_second',
                    'target': 'cpu',
                    'platform': Platform.Android,
                    'max_points': 100,
                }).get_json()
                pk = client.get('/apm/log/pk', query_string={
                    'scene': 'apm_pk',
                    'target1': 'cpu_app1',
                    'target2': 'cpu_app2',
                    'max_points': 100,
                }).get_json()

        self.assertEqual(len(compare['scene1']), 100)
        self.assertEqual(len(compare['scene2']), 100)
        self.assertEqual(compare['scene1'][-1]['y'], 4999)
        self.assertEqual(len(pk['first']), 100)
        self.assertEqual(len(pk['second']), 100)
        self.assertEqual(pk['second'][-1]['y'], 4999)


class TestFastAndroidSummary(unittest.TestCase):

    def test_set_android_perfs_uses_perf_stats_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = File()
            f.report_dir = tmp
            scene = 'apm_fast'
            scene_dir = os.path.join(tmp, scene)
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                json.dump({
                    'app': 'com.test', 'devices': 'dev', 'platform': 'Android',
                    'ctime': '2026-01-01', 'duration_label': 'apm_01:00',
                }, fh)
            perf = {
                'cpu_app': {'avg': 25.5, 'min': 10, 'max': 40},
                'cpu_sys': {'avg': 40.0, 'min': 20, 'max': 50},
                'mem_total': {'avg': 200, 'min': 100, 'max': 300},
                'mem_swap': {'avg': 10, 'min': 0, 'max': 20},
                'fps': {'avg': 60, 'min': 55, 'max': 60},
                'jank': {'sum': 5, 'max': 2, 'stutter_rate': 10},
                'big_jank': {'sum': 1, 'max': 1, 'stutter_rate': 5},
                'gpu': {'avg': 30, 'min': 10, 'max': 50},
            }
            with open(os.path.join(scene_dir, 'perf_stats.json'), 'w', encoding='utf-8') as fh:
                json.dump(perf, fh)
            # huge log that should NOT be read when perf_stats exists
            with open(os.path.join(scene_dir, 'cpu_app.log'), 'w', encoding='utf-8') as fh:
                fh.write('10:00:00.000000=99\n' * 5000)
            apm = f._setAndroidPerfs(scene)
            self.assertEqual(apm['cpuAppRate'], '25.5%')
            self.assertEqual(apm['duration_label'], 'apm_01:00')
            self.assertEqual(apm['jank'], '5')


class TestRemoveReportApi(unittest.TestCase):

    def test_remove_report_deletes_scene_dir(self):
        from solox.web import app
        app.config['TESTING'] = True
        client = app.test_client()
        with tempfile.TemporaryDirectory() as tmp:
            scene = 'apm_to_delete'
            scene_dir = os.path.join(tmp, 'report', scene)
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                json.dump({'app': 'com.test'}, fh)
            with patch('solox.view.apis.os.getcwd', return_value=tmp):
                resp = client.get('/apm/remove/report', query_string={'scene': scene})
            self.assertEqual(resp.get_json()['status'], 1)
            self.assertFalse(os.path.isdir(scene_dir))

    def test_remove_report_rejects_unsafe_scene_paths(self):
        from solox.web import app
        app.config['TESTING'] = True
        client = app.test_client()

        unsafe_scenes = ('..', '../outside', '..\\outside', 'C:\\outside', '/outside')
        with patch('solox.view.apis.shutil.rmtree') as remove:
            for scene in unsafe_scenes:
                with self.subTest(scene=scene):
                    response = client.get(
                        '/apm/remove/report',
                        query_string={'scene': scene},
                    )
                    self.assertEqual(response.get_json()['status'], 0)
            remove.assert_not_called()

    def test_remove_report_rejects_scene_resolving_to_report_root(self):
        from solox.view import apis
        from solox.web import app

        app.config['TESTING'] = True
        client = app.test_client()
        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report')
            os.makedirs(report_root)
            with (
                patch.object(apis.os, 'getcwd', return_value=tmp),
                patch.object(
                    apis.os.path,
                    'realpath',
                    side_effect=(report_root, report_root),
                ),
                patch.object(apis.shutil, 'rmtree') as remove,
            ):
                response = client.get(
                    '/apm/remove/report',
                    query_string={'scene': 'apm_alias'},
                )

        self.assertEqual(response.get_json()['status'], 0)
        remove.assert_not_called()


class TestLogApiPerformance(unittest.TestCase):

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_log_api_only_loads_requested_metric(self):
        from solox.view import apis

        getter_names = (
            'getCpuLog',
            'getMemLog',
            'getMemDetailLog',
            'getBatteryLog',
            'getFlowLog',
            'getFpsLog',
            'getGpuLog',
            'getDiskLog',
            'getCpuCoreLog',
        )
        with ExitStack() as stack:
            mocks = {
                name: stack.enter_context(
                    patch.object(apis.f, name, return_value={'status': 1, 'source': name})
                )
                for name in getter_names
            }
            response = self.client.get('/apm/log', query_string={
                'scene': 'apm_perf',
                'target': 'cpu',
                'platform': Platform.Android,
                'max_points': 200,
            })

        data = response.get_json()
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['source'], 'getCpuLog')
        mocks['getCpuLog'].assert_called_once_with(Platform.Android, 'apm_perf', 200)
        for name, getter in mocks.items():
            if name != 'getCpuLog':
                getter.assert_not_called()

    def test_log_api_clamps_non_positive_max_points(self):
        from solox.view import apis

        with patch.object(
            apis.f,
            'getCpuLog',
            return_value={'status': 1},
        ) as getter:
            for max_points in ('0', '-1', 'abc'):
                with self.subTest(max_points=max_points):
                    response = self.client.get('/apm/log', query_string={
                        'scene': 'apm_perf',
                        'target': 'cpu',
                        'platform': Platform.Android,
                        'max_points': max_points,
                    })
                    self.assertEqual(response.get_json()['status'], 1)

        self.assertEqual(
            getter.call_args_list,
            [
                unittest.mock.call(Platform.Android, 'apm_perf', 1500),
                unittest.mock.call(Platform.Android, 'apm_perf', 1500),
                unittest.mock.call(Platform.Android, 'apm_perf', 1500),
            ],
        )

    def test_log_api_caps_excessive_max_points(self):
        from solox.view import apis

        with patch.object(
            apis.f,
            'getCpuLog',
            return_value={'status': 1},
        ) as getter:
            response = self.client.get('/apm/log', query_string={
                'scene': 'apm_perf',
                'target': 'cpu',
                'platform': Platform.Android,
                'max_points': 999999,
            })

        self.assertEqual(response.get_json()['max_points'], 1500)
        getter.assert_called_once_with(Platform.Android, 'apm_perf', 1500)

    def test_log_api_reads_posted_max_points(self):
        from solox.view import apis

        with patch.object(
            apis.f,
            'getCpuLog',
            return_value={'status': 1},
        ) as getter:
            response = self.client.post('/apm/log', data={
                'scene': 'apm_perf',
                'target': 'cpu',
                'platform': Platform.Android,
                'max_points': '200',
            })

        self.assertEqual(response.get_json()['status'], 1)
        getter.assert_called_once_with(Platform.Android, 'apm_perf', 200)

    def test_log_api_unknown_target_is_stable_and_lazy(self):
        from solox.view import apis

        with patch.object(apis.f, 'getCpuLog') as getter:
            response = self.client.get('/apm/log', query_string={
                'scene': 'apm_perf',
                'target': 'unknown',
                'platform': Platform.Android,
            })

        self.assertEqual(
            response.get_json(),
            {'status': 0, 'msg': 'no target found'},
        )
        getter.assert_not_called()

    def test_log_api_dispatches_all_supported_targets(self):
        from solox.view import apis

        targets = {
            'cpu': 'getCpuLog',
            'mem': 'getMemLog',
            'mem_detail': 'getMemDetailLog',
            'battery': 'getBatteryLog',
            'flow': 'getFlowLog',
            'fps': 'getFpsLog',
            'gpu': 'getGpuLog',
            'disk': 'getDiskLog',
            'cpu_core': 'getCpuCoreLog',
        }
        for target, getter_name in targets.items():
            with self.subTest(target=target):
                with patch.object(
                    apis.f,
                    getter_name,
                    return_value={'status': 1, 'target': target},
                ) as getter:
                    response = self.client.get('/apm/log', query_string={
                        'scene': 'apm_perf',
                        'target': target,
                        'platform': Platform.Android,
                        'max_points': 200,
                    })
                self.assertEqual(response.get_json()['target'], target)
                getter.assert_called_once_with(
                    Platform.Android,
                    'apm_perf',
                    200,
                )

    def test_compare_log_api_passes_max_points(self):
        from solox.view import apis

        with patch.object(
            apis.f,
            'getCpuLogCompare',
            return_value={'status': 1, 'scene1': [], 'scene2': []},
        ) as getter:
            response = self.client.get('/apm/log/compare', query_string={
                'scene1': 'apm_first',
                'scene2': 'apm_second',
                'target': 'cpu',
                'platform': Platform.Android,
                'max_points': 200,
            })

        self.assertEqual(response.get_json()['status'], 1)
        getter.assert_called_once_with(
            Platform.Android,
            'apm_first',
            'apm_second',
            200,
        )

    def test_compare_log_api_preserves_legacy_full_response_without_valid_max_points(self):
        from solox.view import apis

        with patch.object(
            apis.f,
            'getMemLogCompare',
            return_value={'status': 1, 'scene1': [], 'scene2': []},
        ) as getter:
            for max_points in (None, '0', '-1', 'abc'):
                query = {
                    'scene1': 'apm_first',
                    'scene2': 'apm_second',
                    'target': 'memory',
                    'platform': Platform.Android,
                }
                if max_points is not None:
                    query['max_points'] = max_points
                with self.subTest(max_points=max_points):
                    response = self.client.get('/apm/log/compare', query_string=query)
                    self.assertEqual(
                        response.get_json(),
                        {'status': 1, 'scene1': [], 'scene2': []},
                    )

        self.assertEqual(
            getter.call_args_list,
            [
                unittest.mock.call(
                    Platform.Android,
                    'apm_first',
                    'apm_second',
                    None,
                ),
                unittest.mock.call(
                    Platform.Android,
                    'apm_first',
                    'apm_second',
                    None,
                ),
                unittest.mock.call(
                    Platform.Android,
                    'apm_first',
                    'apm_second',
                    None,
                ),
                unittest.mock.call(
                    Platform.Android,
                    'apm_first',
                    'apm_second',
                    None,
                ),
            ],
        )

    def test_compare_and_pk_apis_cap_excessive_max_points(self):
        from solox.view import apis

        with (
            patch.object(
                apis.f,
                'getCpuLogCompare',
                return_value={'status': 1, 'scene1': [], 'scene2': []},
            ) as compare_getter,
            patch.object(
                apis.f,
                'readLog',
                return_value=([], []),
            ) as read_log,
        ):
            compare = self.client.get('/apm/log/compare', query_string={
                'scene1': 'apm_first',
                'scene2': 'apm_second',
                'target': 'cpu',
                'platform': Platform.Android,
                'max_points': 999999,
            }).get_json()
            pk = self.client.get('/apm/log/pk', query_string={
                'scene': 'apm_pk',
                'target1': 'cpu_app1',
                'target2': 'cpu_app2',
                'max_points': 999999,
            }).get_json()

        self.assertEqual(compare['max_points'], 1500)
        self.assertEqual(pk['max_points'], 1500)
        compare_getter.assert_called_once_with(
            Platform.Android,
            'apm_first',
            'apm_second',
            1500,
        )
        self.assertTrue(all(
            call.kwargs['max_points'] == 1500
            for call in read_log.call_args_list
        ))

    def test_pk_log_api_passes_max_points_to_both_logs(self):
        from solox.view import apis

        with patch.object(
            apis.f,
            'readLog',
            side_effect=[([{'x': '1', 'y': 1}], [1]), ([{'x': '1', 'y': 2}], [2])],
        ) as read_log:
            response = self.client.get('/apm/log/pk', query_string={
                'scene': 'apm_pk',
                'target1': 'cpu_app1',
                'target2': 'cpu_app2',
                'max_points': 200,
            })

        self.assertEqual(response.get_json()['status'], 1)
        self.assertEqual(
            read_log.call_args_list,
            [
                unittest.mock.call(
                    scene='apm_pk',
                    filename='cpu_app1.log',
                    max_points=200,
                ),
                unittest.mock.call(
                    scene='apm_pk',
                    filename='cpu_app2.log',
                    max_points=200,
                ),
            ],
        )

    def test_compare_file_getters_downsample_both_scenes(self):
        f = File()
        with patch.object(
            f,
            'readLog',
            return_value=([{'x': '1', 'y': 1}], [1]),
        ) as read_log:
            result = f.getFpsLogCompare(
                Platform.Android,
                'apm_first',
                'apm_second',
                200,
            )

        self.assertEqual(result['status'], 1)
        self.assertEqual(
            read_log.call_args_list,
            [
                unittest.mock.call(
                    scene='apm_first',
                    filename='fps.log',
                    max_points=200,
                ),
                unittest.mock.call(
                    scene='apm_second',
                    filename='fps.log',
                    max_points=200,
                ),
            ],
        )


class TestAnalysisLookupPerformance(unittest.TestCase):

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_analysis_uses_direct_scene_lookup(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            scene_dir = os.path.join(tmp, 'report', 'apm_scene')
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                json.dump({'app': 'com.test'}, fh)
            with (
                patch.object(pages.os, 'getcwd', return_value=tmp),
                patch.object(pages.os, 'listdir', side_effect=AssertionError('full scan')),
                patch.object(pages.f, 'filter_secen', return_value=[]),
                patch.object(
                    pages.f,
                    '_setAndroidPerfs',
                    return_value={'duration_label': 'apm_00:10'},
                ) as summary,
                patch.object(pages.f, 'analysisDisk', return_value=({}, {}, {}, {})),
                patch.object(pages, 'render_template', return_value='ok'),
            ):
                response = self.client.get('/analysis', query_string={
                    'scene': 'apm_scene',
                    'app': 'com.test',
                    'platform': Platform.Android,
                })

        self.assertEqual(response.status_code, 200)
        summary.assert_called_once_with('apm_scene')

    def test_pk_analysis_uses_direct_scene_lookup(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            scene_dir = os.path.join(tmp, 'report', 'apm_scene')
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                json.dump({'app': 'com.test'}, fh)
            with (
                patch.object(pages.os, 'getcwd', return_value=tmp),
                patch.object(pages.os, 'listdir', side_effect=AssertionError('full scan')),
                patch.object(pages.f, '_setpkPerfs', return_value={'status': 1}) as summary,
                patch.object(pages, 'render_template', return_value='ok'),
            ):
                response = self.client.get('/pk_analysis', query_string={
                    'scene': 'apm_scene',
                    'app': 'com.test',
                    'model': '2-app',
                })

        self.assertEqual(response.status_code, 200)
        summary.assert_called_once_with('apm_scene')

    def test_analysis_without_scene_keeps_empty_page_behavior(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'report'))
            with (
                patch.object(pages.os, 'getcwd', return_value=tmp),
                patch.object(pages.f, 'filter_secen', return_value=[]),
                patch.object(pages.f, '_setAndroidPerfs') as summary,
                patch.object(pages, 'render_template', return_value='ok'),
            ):
                response = self.client.get('/analysis', query_string={
                    'platform': Platform.Android,
                })

        self.assertEqual(response.status_code, 200)
        summary.assert_not_called()

    def test_analysis_missing_scene_renders_real_empty_page(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'report'))
            with patch.object(pages.os, 'getcwd', return_value=tmp):
                response = self.client.get('/analysis', query_string={
                    'scene': 'apm_missing',
                    'app': 'com.test',
                    'platform': Platform.Android,
                    'lan': 'cn',
                })

        self.assertEqual(response.status_code, 200)
        self.assertIn('SoloX', response.get_data(as_text=True))

    def test_compare_analysis_missing_scene_renders_real_empty_page(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'report'))
            with patch.object(pages.os, 'getcwd', return_value=tmp):
                response = self.client.get('/compare_analysis', query_string={
                    'scene1': 'apm_first',
                    'scene2': 'apm_second',
                    'app': 'com.test',
                    'platform': Platform.Android,
                    'lan': 'cn',
                })

        self.assertEqual(response.status_code, 200)
        self.assertIn('SoloX', response.get_data(as_text=True))

    def test_pk_analysis_missing_scene_renders_real_empty_page(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'report'))
            with patch.object(pages.os, 'getcwd', return_value=tmp):
                response = self.client.get('/pk_analysis', query_string={
                    'scene': 'apm_missing',
                    'app': 'com.test',
                    'model': '2-app',
                    'lan': 'cn',
                })

        self.assertEqual(response.status_code, 200)
        self.assertIn('SoloX', response.get_data(as_text=True))

    def test_analysis_existing_empty_scene_renders_real_empty_page(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'report', 'apm_empty'))
            with patch.object(pages.os, 'getcwd', return_value=tmp):
                response = self.client.get('/analysis', query_string={
                    'scene': 'apm_empty',
                    'app': 'com.test',
                    'platform': Platform.Android,
                    'lan': 'cn',
                })

        self.assertEqual(response.status_code, 200)
        self.assertIn('SoloX', response.get_data(as_text=True))

    def test_compare_analysis_corrupt_result_json_renders_real_empty_page(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            for scene in ('apm_first', 'apm_second'):
                scene_dir = os.path.join(tmp, 'report', scene)
                os.makedirs(scene_dir)
                with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                    fh.write('{bad json')
            with patch.object(pages.os, 'getcwd', return_value=tmp):
                response = self.client.get('/compare_analysis', query_string={
                    'scene1': 'apm_first',
                    'scene2': 'apm_second',
                    'app': 'com.test',
                    'platform': Platform.Android,
                    'lan': 'cn',
                })

        self.assertEqual(response.status_code, 200)
        self.assertIn('SoloX', response.get_data(as_text=True))

    def test_analysis_rejects_parent_directory_scene(self):
        from solox.view import pages

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'report'))
            with (
                patch.object(pages.os, 'getcwd', return_value=tmp),
                patch.object(pages.f, 'filter_secen', return_value=[]),
                patch.object(pages.f, '_setAndroidPerfs') as summary,
                patch.object(pages, 'render_template', return_value='ok'),
            ):
                response = self.client.get('/analysis', query_string={
                    'scene': '..',
                    'platform': Platform.Android,
                })

        self.assertEqual(response.status_code, 200)
        summary.assert_not_called()

    def test_scene_lookup_rejects_cross_platform_path_forms(self):
        from solox.view.pages import _report_scene_exists

        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report')
            os.makedirs(report_root)
            for scene in (
                '..',
                '../outside',
                '..\\outside',
                '/outside',
                '\\outside',
                'C:\\outside',
                'nested/scene',
                'nested\\scene',
            ):
                with self.subTest(scene=scene):
                    self.assertFalse(_report_scene_exists(report_root, scene))

    def test_analysis_tolerates_report_list_concurrent_changes(self):
        from solox.view import pages

        for error in (
            FileNotFoundError('report removed'),
            ValueError('scene removed'),
        ):
            with self.subTest(error=type(error).__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    scene_dir = os.path.join(tmp, 'report', 'apm_scene')
                    os.makedirs(scene_dir)
                    with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                        json.dump({'app': 'com.test'}, fh)
                    with (
                        patch.object(pages.os, 'getcwd', return_value=tmp),
                        patch.object(pages.f, 'filter_secen', side_effect=error),
                        patch.object(
                            pages.f,
                            '_setAndroidPerfs',
                            return_value={'duration_label': 'apm_00:10'},
                        ) as summary,
                        patch.object(
                            pages.f,
                            'analysisDisk',
                            return_value=({}, {}, {}, {}),
                        ),
                        patch.object(pages, 'render_template', return_value='ok'),
                    ):
                        response = self.client.get('/analysis', query_string={
                            'scene': 'apm_scene',
                            'platform': Platform.Android,
                        })

                self.assertEqual(response.status_code, 200)
                summary.assert_called_once_with('apm_scene')


class TestReportListPerformance(unittest.TestCase):

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    @staticmethod
    def _write_report(report_root, scene, timestamp):
        scene_dir = os.path.join(report_root, scene)
        os.makedirs(scene_dir)
        with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
            json.dump({'app': scene, 'duration': '00:10', 'duration_label': 'apm_00:10'}, fh)
        os.utime(scene_dir, (timestamp, timestamp))

    def test_report_list_counts_only_directories_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report')
            os.makedirs(report_root)
            self._write_report(report_root, 'apm_old', 1000)
            self._write_report(report_root, 'apm_new', 2000)
            unrelated = os.path.join(report_root, 'README')
            with open(unrelated, 'w', encoding='utf-8') as fh:
                fh.write('not a report')
            os.utime(unrelated, (3000, 3000))

            with patch('solox.view.apis.os.getcwd', return_value=tmp):
                response = self.client.get('/apm/report/list', query_string={
                    'page': 1,
                    'size': 1,
                })

        data = response.get_json()
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['scene'], 'apm_new')

    def test_report_list_keeps_legacy_extension_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report')
            os.makedirs(report_root)
            self._write_report(report_root, 'apm_valid', 1000)
            self._write_report(report_root, 'archived.log', 2000)

            with patch('solox.view.apis.os.getcwd', return_value=tmp):
                response = self.client.get('/apm/report/list')

        data = response.get_json()
        self.assertEqual(data['total'], 1)
        self.assertEqual([item['scene'] for item in data['data']], ['apm_valid'])

    def test_report_list_skips_entry_deleted_during_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene_dir = os.path.join(tmp, 'report', 'apm_gone')
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                json.dump({'app': 'gone'}, fh)
            disappearing = MagicMock()
            disappearing.is_dir.return_value = True
            disappearing.name = 'apm_gone'
            disappearing.path = scene_dir
            disappearing.stat.side_effect = FileNotFoundError('removed')
            with (
                patch('solox.view.apis.os.getcwd', return_value=tmp),
                patch('solox.view.apis.os.scandir', return_value=[disappearing]),
            ):
                response = self.client.get('/apm/report/list')

        data = response.get_json()
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['data'], [])

    def test_report_list_reads_metadata_as_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report')
            os.makedirs(report_root)
            self._write_report(report_root, 'apm_utf8', 1000)
            result_path = os.path.join(report_root, 'apm_utf8', 'result.json')
            with open(result_path, 'w', encoding='utf-8') as fh:
                json.dump(
                    {'app': '中文应用', 'duration_label': 'apm_00:10'},
                    fh,
                    ensure_ascii=False,
                )

            with (
                patch('solox.view.apis.os.getcwd', return_value=tmp),
                patch('solox.view.apis.open', wraps=open) as open_file,
            ):
                response = self.client.get('/apm/report/list')

        self.assertEqual(response.get_json()['data'][0]['app'], '中文应用')
        result_calls = [
            call for call in open_file.call_args_list
            if call.args and call.args[0] == result_path
        ]
        self.assertEqual(len(result_calls), 1)
        self.assertEqual(result_calls[0].kwargs.get('encoding'), 'utf-8')

    def test_report_list_excludes_invalid_metadata_before_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report')
            os.makedirs(report_root)
            self._write_report(report_root, 'apm_valid', 1000)
            invalid_dir = os.path.join(report_root, 'apm_invalid')
            os.makedirs(invalid_dir)
            with open(os.path.join(invalid_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                fh.write('{invalid json')
            os.utime(invalid_dir, (2000, 2000))
            invalid_type_dir = os.path.join(report_root, 'apm_invalid_type')
            os.makedirs(invalid_type_dir)
            with open(
                os.path.join(invalid_type_dir, 'result.json'),
                'w',
                encoding='utf-8',
            ) as fh:
                json.dump([], fh)
            os.utime(invalid_type_dir, (3000, 3000))

            with patch('solox.view.apis.os.getcwd', return_value=tmp):
                response = self.client.get('/apm/report/list', query_string={
                    'page': 1,
                    'size': 1,
                })

        data = response.get_json()
        self.assertEqual(data['total'], 3)
        self.assertEqual([item['scene'] for item in data['data']], ['apm_valid'])

    def test_report_list_reads_only_enough_metadata_for_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report')
            os.makedirs(report_root)
            for index in range(300):
                self._write_report(
                    report_root,
                    f'apm_{index:03d}',
                    1000 + index,
                )

            with (
                patch('solox.view.apis.os.getcwd', return_value=tmp),
                patch('solox.view.apis.open', wraps=open) as open_file,
            ):
                response = self.client.get('/apm/report/list', query_string={
                    'page': 1,
                    'size': 1,
                })

        self.assertEqual(response.get_json()['data'][0]['scene'], 'apm_299')
        result_reads = [
            call for call in open_file.call_args_list
            if call.args and str(call.args[0]).endswith('result.json')
        ]
        self.assertLessEqual(len(result_reads), 2)


if __name__ == '__main__':
    unittest.main()
