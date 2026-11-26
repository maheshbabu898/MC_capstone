import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'api_client.dart';

const _ink = Color(0xFF101828);
const _muted = Color(0xFF667085);
const _accent = Color(0xFF5869D8);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MecApplication());
}

Map<String, dynamic> _runMobileWorkload(Map<String, int> input) {
  final iterations = input['iterations']!;
  const mask = 0x7fffffffffffffff;
  var checksum = 0x9e3779b9;
  for (var index = 0; index < iterations; index++) {
    checksum ^= (index + 0x85ebca6b);
    checksum = ((checksum << 7) | (checksum >> 56)) & mask;
    checksum = (checksum * 0xc2b2ae35) & mask;
  }
  return {
    'iterations': iterations,
    'checksum': checksum.toRadixString(16),
    'workload': 'mobile integer-mixing CPU workload',
  };
}

class MecApplication extends StatelessWidget {
  const MecApplication({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'MEC Intelligent Offloading',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: _accent),
          scaffoldBackgroundColor: const Color(0xFFF5F7FB),
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFFF5F7FB),
            foregroundColor: _ink,
            elevation: 0,
          ),
          cardTheme: CardThemeData(
            elevation: 0,
            color: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: const Color(0xFFF7F8FC),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(13),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        home: const SplashScreen(),
      );
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    unawaited(_prepare());
  }

  Future<void> _prepare() async {
    await ApiClient.loadSettings();
    await Future<void>.delayed(const Duration(milliseconds: 650));
    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(builder: (_) => const LoginScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) => const Scaffold(
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _BrandMark(size: 66),
              SizedBox(height: 18),
              Text('MEC Intelligent Offloading',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 22)),
              SizedBox(height: 14),
              CircularProgressIndicator(),
            ],
          ),
        ),
      );
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _name = TextEditingController();

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  void _continue() => Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => HomeScreen(displayName: _name.text.trim()),
        ),
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 430),
            child: Padding(
              padding: const EdgeInsets.all(26),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const _BrandMark(size: 58),
                  const SizedBox(height: 22),
                  Text('Welcome to MEC',
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          )),
                  const SizedBox(height: 8),
                  const Text(
                    'Explore intelligent task placement across mobile, edge, and cloud.',
                    style: TextStyle(color: _muted, height: 1.5),
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _name,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _continue(),
                    decoration: const InputDecoration(
                      labelText: 'Your name (optional)',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                  ),
                  const SizedBox(height: 15),
                  FilledButton(
                    onPressed: _continue,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(52),
                    ),
                    child: const Text('Continue as guest'),
                  ),
                  const SizedBox(height: 9),
                  const Text(
                    'Guest access · This project does not require an account.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: _muted, fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.displayName});

  final String displayName;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  int _refreshKey = 0;

  List<Widget> get _pages => [
        DashboardScreen(
          displayName: widget.displayName,
          refreshKey: _refreshKey,
          onCreateTask: () => setState(() => _selectedIndex = 1),
          onOpenHistory: () => setState(() => _selectedIndex = 4),
        ),
        TaskFlowScreen(
          onCompleted: () => setState(() => _refreshKey++),
        ),
        AnalyticsScreen(refreshKey: _refreshKey),
        MonitoringScreen(refreshKey: _refreshKey),
        HistoryScreen(refreshKey: _refreshKey),
      ];

  static const _destinations = [
    NavigationDestination(icon: Icon(Icons.space_dashboard_outlined),
        selectedIcon: Icon(Icons.space_dashboard), label: 'Home'),
    NavigationDestination(icon: Icon(Icons.add_task_outlined),
        selectedIcon: Icon(Icons.add_task), label: 'Tasks'),
    NavigationDestination(icon: Icon(Icons.insights_outlined),
        selectedIcon: Icon(Icons.insights), label: 'Analytics'),
    NavigationDestination(icon: Icon(Icons.dns_outlined),
        selectedIcon: Icon(Icons.dns), label: 'Servers'),
    NavigationDestination(icon: Icon(Icons.history_outlined),
        selectedIcon: Icon(Icons.history), label: 'History'),
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Row(
            children: [
              _BrandMark(size: 30),
              SizedBox(width: 10),
              Text('MEC Intelligent Offloading',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            ],
          ),
          actions: [
            IconButton(
              tooltip: 'Settings',
              onPressed: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => const SettingsScreen(),
                  ),
                );
                if (mounted) setState(() => _refreshKey++);
              },
              icon: const Icon(Icons.settings_outlined),
            ),
            const SizedBox(width: 4),
          ],
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 850),
              child: IndexedStack(index: _selectedIndex, children: _pages),
            ),
          ),
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          destinations: _destinations,
          onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        ),
      );
}

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({
    super.key,
    required this.displayName,
    required this.refreshKey,
    required this.onCreateTask,
    required this.onOpenHistory,
  });

  final String displayName;
  final int refreshKey;
  final VoidCallback onCreateTask;
  final VoidCallback onOpenHistory;

  @override
  Widget build(BuildContext context) => _AsyncPanel(
        key: ValueKey(refreshKey),
        path: '/api/analytics/performance',
        builder: (context, summary) {
          final distribution = summary['location_distribution'] as Map? ?? {};
          return ListView(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 28),
            children: [
              Text(
                displayName.isEmpty ? 'Your MEC dashboard' : 'Hello, $displayName',
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              const Text('Track workloads and intelligent offloading decisions.',
                  style: TextStyle(color: _muted)),
              const SizedBox(height: 20),
              Row(children: [
                Expanded(child: _MetricCard(
                  title: 'Tasks completed',
                  value: '${summary['completed'] ?? 0}',
                  icon: Icons.task_alt,
                  tint: const Color(0xFFDCF4EB),
                )),
                const SizedBox(width: 12),
                Expanded(child: _MetricCard(
                  title: 'Execution paths',
                  value: '${distribution.length}',
                  icon: Icons.hub_outlined,
                  tint: const Color(0xFFE9E9FD),
                )),
              ]),
              const SizedBox(height: 13),
              Row(children: [
                Expanded(child: _MetricCard(
                  title: 'Avg. processing',
                  value: _formatSeconds(summary['average_execution_seconds']),
                  icon: Icons.timer_outlined,
                  tint: const Color(0xFFFFF0D8),
                )),
                const SizedBox(width: 12),
                Expanded(child: _MetricCard(
                  title: 'Failed tasks',
                  value: '${summary['failed'] ?? 0}',
                  icon: Icons.warning_amber_outlined,
                  tint: const Color(0xFFFCE6E8),
                )),
              ]),
              const SizedBox(height: 20),
              _SectionCard(
                title: 'Execution distribution',
                subtitle: 'Where completed workloads ran',
                child: distribution.isEmpty
                    ? const _EmptyMessage('Create a task to start your history.')
                    : Column(
                        children: distribution.entries.map<Widget>((entry) {
                          final name = entry.key.toString();
                          final count = (entry.value as num).toInt();
                          return ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: CircleAvatar(
                              backgroundColor: _locationColor(name).withValues(alpha: .12),
                              child: Icon(_locationIcon(name), color: _locationColor(name)),
                            ),
                            title: Text(name.toUpperCase(),
                                style: const TextStyle(fontWeight: FontWeight.w700)),
                            trailing: Text('$count tasks',
                                style: const TextStyle(color: _muted)),
                          );
                        }).toList(),
                      ),
              ),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: onCreateTask,
                icon: const Icon(Icons.add),
                label: const Text('Create or upload a task'),
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
              ),
              TextButton.icon(
                onPressed: onOpenHistory,
                icon: const Icon(Icons.history),
                label: const Text('View task history'),
              ),
            ],
          );
        },
      );
}

class TaskFlowScreen extends StatefulWidget {
  const TaskFlowScreen({super.key, required this.onCompleted});

  final VoidCallback onCompleted;

  @override
  State<TaskFlowScreen> createState() => _TaskFlowScreenState();
}

class _TaskFlowScreenState extends State<TaskFlowScreen> {
  final _cycles = TextEditingController(text: '0.05');
  final _picker = ImagePicker();
  String _type = 'compute';
  PlatformFile? _document;
  String? _imagePath;
  Map<String, dynamic>? _task;
  Map<String, dynamic>? _decision;
  Map<String, dynamic>? _execution;
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _cycles.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final image = await _picker.pickImage(source: ImageSource.gallery);
    if (image != null && mounted) {
      setState(() {
        _imagePath = image.path;
        _document = null;
      });
    }
  }

  Future<void> _pickDocument() async {
    final selected = await FilePicker.platform.pickFiles(type: FileType.custom,
        allowedExtensions: const ['pdf', 'docx', 'txt']);
    if (selected != null && selected.files.isNotEmpty && mounted) {
      setState(() {
        _document = selected.files.first;
        _imagePath = null;
      });
    }
  }

  Future<void> _createAndDecide() async {
    setState(() {
      _busy = true;
      _error = null;
      _decision = null;
      _execution = null;
      _task = null;
    });
    try {
      final cycles = double.parse(_cycles.text);
      if (cycles <= 0 || cycles > 2) {
        throw const FormatException('CPU cycles must be between 0 and 2 Giga-cycles.');
      }
      final dynamic created;
      if (_type == 'compute') {
        created = await ApiClient.post('/api/tasks/create', {
          'task_type': _type,
          'name': 'Mobile compute workload',
          'input_size_mb': 0.1,
          'cpu_cycles_giga': cycles,
        });
      } else if (_type == 'image') {
        if (_imagePath == null) throw const FormatException('Select an image first.');
        created = await ApiClient.upload(
          PlatformFile(name: _imagePath!.split(RegExp(r'[/\\]')).last,
              path: _imagePath, size: 0),
          'image',
          cycles,
        );
      } else {
        if (_document == null) throw const FormatException('Select a document first.');
        created = await ApiClient.upload(_document!, 'document', cycles);
      }
      final taskId = created['id'].toString();
      final decision = await ApiClient.post(
          '/api/offloading/decide', {'task_id': taskId});
      if (!mounted) return;
      setState(() {
        _task = Map<String, dynamic>.from(created as Map);
        _decision = Map<String, dynamic>.from(decision as Map);
      });
      widget.onCompleted();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _execute() async {
    if (_task == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final isMobileCompute =
          _decision?['location'] == 'local' && _task?['task_type'] == 'compute';
      final Map<String, dynamic> execution;
      if (isMobileCompute) {
        final cycles = _number(_task?['cpu_cycles_giga']);
        final iterations = (cycles * 500000).round().clamp(1, 1000000).toInt();
        final stopwatch = Stopwatch()..start();
        final result = await compute(
          _runMobileWorkload,
          {'iterations': iterations},
        );
        stopwatch.stop();
        final response = await ApiClient.post('/api/offloading/execute', {
          'task_id': _task!['id'],
          'client_execution_seconds': stopwatch.elapsedMicroseconds / 1000000,
          'client_result': result,
        });
        execution = Map<String, dynamic>.from(response as Map);
      } else {
        final response = await ApiClient.post(
            '/api/offloading/execute', {'task_id': _task!['id']});
        execution = Map<String, dynamic>.from(response as Map);
      }
      if (!mounted) return;
      setState(() => _execution = execution);
      widget.onCompleted();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Text('Task processing',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  )),
          const SizedBox(height: 6),
          const Text('Prepare a workload, review the AI placement, and execute it.',
              style: TextStyle(color: _muted)),
          const SizedBox(height: 18),
          _SectionCard(
            title: '1 · Prepare a task',
            subtitle: 'Image inference uses pretrained MobileNetV2 model weights.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                DropdownButtonFormField<String>(
                  value: _type,
                  decoration: const InputDecoration(labelText: 'Task type'),
                  items: const [
                    DropdownMenuItem(value: 'compute', child: Text('CPU computation')),
                    DropdownMenuItem(value: 'image', child: Text('Image recognition')),
                    DropdownMenuItem(value: 'document', child: Text('Document extraction')),
                  ],
                  onChanged: _busy
                      ? null
                      : (value) => setState(() {
                            _type = value ?? 'compute';
                            _imagePath = null;
                            _document = null;
                          }),
                ),
                const SizedBox(height: 13),
                if (_type == 'image')
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _pickImage,
                    icon: const Icon(Icons.image_outlined),
                    label: Text(_imagePath == null
                        ? 'Choose image from gallery'
                        : _imagePath!.split(RegExp(r'[/\\]')).last),
                  ),
                if (_type == 'document')
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _pickDocument,
                    icon: const Icon(Icons.attach_file),
                    label: Text(_document?.name ?? 'Choose PDF, DOCX, or TXT'),
                  ),
                TextField(
                  controller: _cycles,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'CPU workload (Giga-cycles)',
                    helperText: 'Between 0 and 2 Giga-cycles.',
                  ),
                ),
                const SizedBox(height: 14),
                FilledButton(
                  onPressed: _busy ? null : _createAndDecide,
                  child: Text(_busy ? 'Preparing task…' : 'Create and get AI decision'),
                ),
              ],
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            _ErrorPanel(message: _error!),
          ],
          if (_decision case final decision?) ...[
            const SizedBox(height: 14),
            _SectionCard(
              title: '2 · AI offloading decision',
              subtitle: 'Task ${_task?['id']?.toString().substring(0, 8) ?? ''}',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _DecisionBadge(location: decision['location']?.toString() ?? 'local'),
                  const SizedBox(height: 10),
                  Text('Policy · ${_pretty(decision['policy'])}',
                      style: const TextStyle(color: _muted)),
                  const SizedBox(height: 15),
                  Row(children: [
                    Expanded(child: _SmallMetric(
                      'Latency estimate',
                      '${_number(decision['estimated_latency_ms']).toStringAsFixed(1)} ms',
                    )),
                    Expanded(child: _SmallMetric(
                      'Energy estimate',
                      '${_number(decision['estimated_energy_joules']).toStringAsFixed(2)} J',
                    )),
                    Expanded(child: _SmallMetric(
                      'Reward',
                      _number(decision['reward']).toStringAsFixed(3),
                    )),
                  ]),
                  const SizedBox(height: 12),
                  const Text(
                    'Latency and energy are simulator estimates, not device measurements.',
                    style: TextStyle(color: _muted, fontSize: 11),
                  ),
                  const SizedBox(height: 15),
                  FilledButton.icon(
                    onPressed: _busy || _execution != null ? null : _execute,
                    icon: const Icon(Icons.play_arrow),
                    label: Text(_execution == null
                        ? 'Execute on ${_pretty(decision['location'])}'
                        : 'Execution complete'),
                  ),
                ],
              ),
            ),
          ],
          if (_execution case final execution?) ...[
            const SizedBox(height: 14),
            _SectionCard(
              title: '3 · Execution result',
              subtitle: 'Processed on ${_pretty(execution['location'])}',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SmallMetric('Measured processing',
                      '${_number(execution['execution_seconds']).toStringAsFixed(3)} s'),
                  const SizedBox(height: 12),
                  _ResultView(result: execution['result']),
                ],
              ),
            ),
          ],
          const SizedBox(height: 14),
          const _SectionCard(
            title: 'Processing modes',
            subtitle: 'The service performs the chosen workload on the selected server.',
            child: Column(
              children: [
                _FeatureRow(icon: Icons.memory, title: 'Compute',
                    subtitle: 'Bounded repeated SHA-256 CPU workload'),
                _FeatureRow(icon: Icons.image_outlined, title: 'Image',
                    subtitle: 'MobileNetV2 top-five ImageNet predictions'),
                _FeatureRow(icon: Icons.description_outlined, title: 'Documents',
                    subtitle: 'PDF, DOCX, and UTF-8 text extraction'),
              ],
            ),
          ),
        ],
      );
}

class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key, required this.refreshKey});

  final int refreshKey;

  @override
  Widget build(BuildContext context) => _AsyncPanel(
        key: ValueKey(refreshKey),
        path: '/api/analytics/comparison?tasks=30&seed=42',
        builder: (context, data) {
          final rows = (data['comparison'] as List? ?? const [])
              .cast<Map<String, dynamic>>();
          return ListView(
            padding: const EdgeInsets.all(18),
            children: [
              Text('Performance analytics',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      )),
              const SizedBox(height: 5),
              const Text('Reproducible simulated task scenarios across six policies.',
                  style: TextStyle(color: _muted)),
              const SizedBox(height: 16),
              if (data['results_are_simulated'] == true)
                const _InfoPanel(
                    text: 'Latency, energy, and success-rate comparisons are simulated estimates.'),
              const SizedBox(height: 10),
              _BenchmarkBarChart(
                title: 'Estimated latency by policy',
                rows: rows,
                metric: 'average_latency_seconds',
                unit: 's',
                color: const Color(0xFF5869D8),
              ),
              const SizedBox(height: 11),
              _BenchmarkBarChart(
                title: 'Estimated energy by policy',
                rows: rows,
                metric: 'average_energy_joules',
                unit: 'J',
                color: const Color(0xFF14856B),
              ),
              const SizedBox(height: 11),
              _BenchmarkBarChart(
                title: 'Simulated success rate by policy',
                rows: rows,
                metric: 'success_rate',
                unit: '%',
                color: const Color(0xFFB97417),
                percentage: true,
              ),
              const SizedBox(height: 11),
              for (final row in rows) ...[
                _SectionCard(
                  title: _pretty(row['policy']),
                  subtitle: 'Mean reward ${_number(row['average_reward']).toStringAsFixed(3)}',
                  child: Column(children: [
                    _FeatureRow(
                      icon: Icons.timer_outlined,
                      title: 'Latency',
                      subtitle:
                          '${_number(row['average_latency_seconds']).toStringAsFixed(3)} s estimated',
                    ),
                    _FeatureRow(
                      icon: Icons.bolt_outlined,
                      title: 'Energy',
                      subtitle:
                          '${_number(row['average_energy_joules']).toStringAsFixed(3)} J estimated',
                    ),
                    _FeatureRow(
                      icon: Icons.check_circle_outline,
                      title: 'Success',
                      subtitle:
                          '${(_number(row['success_rate']) * 100).toStringAsFixed(1)}% simulated',
                    ),
                  ]),
                ),
                const SizedBox(height: 10),
              ],
              if (rows.isEmpty) const _EmptyMessage('No benchmark results are available.'),
            ],
          );
        },
      );
}

class MonitoringScreen extends StatelessWidget {
  const MonitoringScreen({super.key, required this.refreshKey});

  final int refreshKey;

  @override
  Widget build(BuildContext context) => _AsyncPanel(
        key: ValueKey(refreshKey),
        path: '/api/monitoring/resources',
        builder: (context, data) {
          final mobile = data['mobile'] as Map? ?? {};
          final edge = data['edge'] as Map? ?? {};
          final cloud = data['cloud'] as Map? ?? {};
          final network = data['network'] as Map? ?? {};
          return ListView(
            padding: const EdgeInsets.all(18),
            children: [
              Text('Server monitoring',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      )),
              const SizedBox(height: 5),
              const Text('Resource samples and edge/cloud service availability.',
                  style: TextStyle(color: _muted)),
              const SizedBox(height: 17),
              for (final server in [
                ('Mobile / API host', mobile, true),
                ('Edge server', edge, edge['available'] == true),
                ('Cloud server', cloud, cloud['available'] == true),
              ]) ...[
                _SectionCard(
                  title: server.$1,
                  subtitle: server.$3 ? 'Service available' : 'Service unavailable',
                  child: Column(
                    children: [
                      _ResourceMeter(
                        label: 'CPU utilization',
                        value: server.$2['cpu_utilization'],
                      ),
                      _ResourceMeter(
                        label: 'Memory utilization',
                        value: server.$2['memory_utilization'],
                      ),
                      if (server.$2['active_tasks'] != null)
                        _FeatureRow(
                          icon: Icons.pending_actions,
                          title: 'Active tasks',
                          subtitle: '${server.$2['active_tasks']}',
                        ),
                      if (server.$2['error'] != null)
                        Text(server.$2['error'].toString(),
                            style: const TextStyle(color: Colors.red)),
                    ],
                  ),
                ),
                const SizedBox(height: 11),
              ],
              _SectionCard(
                title: 'Network model',
                subtitle: 'Configured simulation values',
                child: Column(
                  children: [
                    _FeatureRow(
                      icon: Icons.network_check,
                      title: 'Latency estimate',
                      subtitle: '${network['latency_ms'] ?? '—'} ms',
                    ),
                    _FeatureRow(
                      icon: Icons.speed,
                      title: 'Bandwidth estimate',
                      subtitle: '${network['bandwidth_mbps'] ?? '—'} Mbps',
                    ),
                    Text(
                      network['source']?.toString() ?? 'Estimated, not measured.',
                      style: const TextStyle(color: _muted, fontSize: 11),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      );
}

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key, required this.refreshKey});

  final int refreshKey;

  @override
  Widget build(BuildContext context) => _AsyncPanel(
        key: ValueKey(refreshKey),
        path: '/api/tasks?limit=100',
        builder: (context, data) {
          final items = (data['items'] as List? ?? const []).cast<Map<String, dynamic>>();
          return ListView(
            padding: const EdgeInsets.all(18),
            children: [
              Text('Task history',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      )),
              const SizedBox(height: 5),
              Text('${data['count'] ?? 0} persisted task(s)',
                  style: const TextStyle(color: _muted)),
              const SizedBox(height: 14),
              if (items.isEmpty) const _EmptyMessage('Your completed and pending tasks will appear here.'),
              for (final task in items) ...[
                _SectionCard(
                  title: task['name']?.toString() ?? 'Task',
                  subtitle: '${_pretty(task['task_type'])} · ${_pretty(task['status'])}',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (task['execution_location'] != null)
                        _DecisionBadge(location: task['execution_location'].toString()),
                      if (task['execution_seconds'] != null)
                        _FeatureRow(
                          icon: Icons.timer_outlined,
                          title: 'Measured processing',
                          subtitle:
                              '${_number(task['execution_seconds']).toStringAsFixed(3)} s',
                        ),
                      if (task['error_message'] != null)
                        Text(task['error_message'].toString(),
                            style: const TextStyle(color: Colors.red)),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
              ],
            ],
          );
        },
      );
}

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _urlController;
  String? _message;
  bool _saved = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: ApiClient.baseUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _saved = false;
    });
    try {
      await ApiClient.saveBaseUrl(_urlController.text);
      await ApiClient.get('/health');
      if (mounted) {
        setState(() {
          _saved = true;
          _message = 'Backend URL saved. API health check succeeded.';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _saved = false;
          _message = 'Unable to reach the backend: $error';
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Settings')),
        body: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            _SectionCard(
              title: 'Backend connection',
              subtitle: 'Set the API address reachable from this device.',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _urlController,
                    keyboardType: TextInputType.url,
                    decoration: const InputDecoration(
                      labelText: 'Backend API URL',
                      hintText: 'http://10.0.2.2:8000',
                      prefixIcon: Icon(Icons.link),
                    ),
                  ),
                  const SizedBox(height: 7),
                  const Text(
                    'Android emulator: 10.0.2.2 · Physical phone: your computer LAN IP.',
                    style: TextStyle(color: _muted, fontSize: 11),
                  ),
                  const SizedBox(height: 14),
                  FilledButton(
                    onPressed: _busy ? null : _save,
                    child: Text(_busy ? 'Checking…' : 'Save and check connection'),
                  ),
                  if (_message case final message?) ...[
                    const SizedBox(height: 10),
                    Text(message,
                        style: TextStyle(
                          color: _saved
                              ? const Color(0xFF18794E)
                              : Theme.of(context).colorScheme.error,
                        )),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 13),
            const _InfoPanel(
              text: 'Login is provided as guest access. This project does not implement a user-account or authentication service.',
            ),
            const SizedBox(height: 13),
            const _InfoPanel(
              text: 'Latency and energy are modeled estimates. Workload processing duration is measured by the server that runs it.',
            ),
          ],
        ),
      );
}

class _AsyncPanel extends StatelessWidget {
  const _AsyncPanel({
    super.key,
    required this.path,
    required this.builder,
  });

  final String path;
  final Widget Function(BuildContext, Map<String, dynamic>) builder;

  @override
  Widget build(BuildContext context) => FutureBuilder<dynamic>(
        future: ApiClient.get(path),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: _ErrorPanel(message: snapshot.error.toString()),
              ),
            );
          }
          if (snapshot.data is! Map) {
            return const Center(child: _ErrorPanel(message: 'Unexpected backend response.'));
          }
          return builder(context, Map<String, dynamic>.from(snapshot.data as Map));
        },
      );
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(17),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 4),
              Text(subtitle, style: const TextStyle(color: _muted, fontSize: 12)),
              const SizedBox(height: 14),
              child,
            ],
          ),
        ),
      );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.tint,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color tint;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: 17,
                backgroundColor: tint,
                child: Icon(icon, size: 18, color: _accent),
              ),
              const SizedBox(height: 12),
              Text(value,
                  style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w800)),
              const SizedBox(height: 3),
              Text(title,
                  style: const TextStyle(color: _muted, fontSize: 11)),
            ],
          ),
        ),
      );
}

class _DecisionBadge extends StatelessWidget {
  const _DecisionBadge({required this.location});

  final String location;

  @override
  Widget build(BuildContext context) {
    final color = _locationColor(location);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .1),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(children: [
        Icon(_locationIcon(location), color: color),
        const SizedBox(width: 10),
        Text(location.toUpperCase(),
            style: TextStyle(color: color, fontWeight: FontWeight.w800, letterSpacing: 1)),
      ]),
    );
  }
}

class _SmallMetric extends StatelessWidget {
  const _SmallMetric(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: _muted, fontSize: 10)),
          const SizedBox(height: 4),
          Text(value,
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        ],
      );
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(icon, color: _accent),
        title: Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle, style: const TextStyle(color: _muted, fontSize: 11)),
        dense: true,
      );
}

class _ResourceMeter extends StatelessWidget {
  const _ResourceMeter({required this.label, required this.value});

  final String label;
  final dynamic value;

  @override
  Widget build(BuildContext context) {
    final fraction = value is num ? value.toDouble().clamp(0, 1).toDouble() : null;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(label, style: const TextStyle(color: _muted, fontSize: 12)),
            Text(fraction == null ? 'Unavailable' : '${(fraction * 100).toStringAsFixed(0)}%',
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
          ]),
          const SizedBox(height: 6),
          LinearProgressIndicator(
            value: fraction,
            minHeight: 5,
            borderRadius: BorderRadius.circular(8),
            backgroundColor: const Color(0xFFE9ECF3),
          ),
        ],
      ),
    );
  }
}

class _InfoPanel extends StatelessWidget {
  const _InfoPanel({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: const Color(0xFFEDEFFF),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.info_outline, color: _accent, size: 18),
          const SizedBox(width: 9),
          Expanded(child: Text(text, style: const TextStyle(color: _ink, fontSize: 12, height: 1.4))),
        ]),
      );
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFFFEBEE),
          borderRadius: BorderRadius.circular(13),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.error_outline, color: Color(0xFFB42336)),
          const SizedBox(width: 9),
          Expanded(child: Text(message, style: const TextStyle(color: Color(0xFF8F1D2D)))),
        ]),
      );
}

class _EmptyMessage extends StatelessWidget {
  const _EmptyMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 17),
        child: Center(child: Text(message, textAlign: TextAlign.center,
            style: const TextStyle(color: _muted))),
      );
}

class _BrandMark extends StatelessWidget {
  const _BrandMark({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF7C8DFF), _accent]),
          borderRadius: BorderRadius.circular(size * .28),
        ),
        alignment: Alignment.center,
        child: Text('M',
            style: TextStyle(
                color: Colors.white, fontWeight: FontWeight.w800, fontSize: size * .5)),
      );
}

String _pretty(dynamic value) => (value?.toString() ?? 'unknown')
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word.isEmpty ? word : '${word[0].toUpperCase()}${word.substring(1)}')
    .join(' ');

double _number(dynamic value) => value is num ? value.toDouble() : 0;

String _formatSeconds(dynamic value) =>
    value is num ? '${value.toStringAsFixed(3)} s' : '—';

Color _locationColor(String location) => switch (location.toLowerCase()) {
      'edge' => const Color(0xFF14856B),
      'cloud' => const Color(0xFF7351B7),
      _ => _accent,
    };

IconData _locationIcon(String location) => switch (location.toLowerCase()) {
      'edge' => Icons.router_outlined,
      'cloud' => Icons.cloud_outlined,
      _ => Icons.phone_android_outlined,
    };

class _ResultView extends StatelessWidget {
  const _ResultView({required this.result});

  final dynamic result;

  @override
  Widget build(BuildContext context) {
    if (result is! Map) {
      return Text(result?.toString() ?? 'No workload output.');
    }
    final data = Map<String, dynamic>.from(result as Map);
    final labels = data['labels'];
    if (labels is List) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('MobileNetV2 top predictions',
              style: TextStyle(fontWeight: FontWeight.w700)),
          for (final item in labels.whereType<Map>())
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(item['label']?.toString() ?? 'Unknown'),
              trailing: Text(
                '${(_number(item['confidence']) * 100).toStringAsFixed(1)}%',
              ),
            ),
        ],
      );
    }
    if (data['text'] is String) {
      final text = data['text'].toString();
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${data['characters_extracted'] ?? text.length} characters extracted'),
          const SizedBox(height: 8),
          SelectableText(text.isEmpty ? 'No extractable text found.' : text),
        ],
      );
    }
    return SelectableText(const JsonEncoder.withIndent('  ').convert(data));
  }
}

class _BenchmarkBarChart extends StatelessWidget {
  const _BenchmarkBarChart({
    required this.title,
    required this.rows,
    required this.metric,
    required this.unit,
    required this.color,
    this.percentage = false,
  });

  final String title;
  final List<Map<String, dynamic>> rows;
  final String metric;
  final String unit;
  final Color color;
  final bool percentage;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox.shrink();
    final values = rows.map((row) {
      final value = _number(row[metric]);
      return percentage ? value * 100 : value;
    }).toList();
    final largest = values.reduce((left, right) => left > right ? left : right);
    final maximum = largest * 1.2 < 0.1 ? 0.1 : largest * 1.2;
    final labels = rows
        .map((row) => _pretty(row['policy']).replaceAll(' ', '\n'))
        .toList();
    return _SectionCard(
      title: title,
      subtitle: percentage
          ? 'Seeded simulation · higher is better'
          : 'Seeded simulation · lower is better',
      child: SizedBox(
        height: 245,
        child: BarChart(
          BarChartData(
            maxY: maximum,
            alignment: BarChartAlignment.spaceAround,
            gridData: FlGridData(show: true, drawVerticalLine: false),
            borderData: FlBorderData(show: false),
            titlesData: FlTitlesData(
              leftTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false)),
              rightTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false)),
              topTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false)),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 43,
                  getTitlesWidget: (value, meta) {
                    final index = value.toInt();
                    if (index < 0 || index >= labels.length) {
                      return const SizedBox.shrink();
                    }
                    return Padding(
                      padding: const EdgeInsets.only(top: 7),
                      child: Text(
                        labels[index],
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 8, color: _muted),
                      ),
                    );
                  },
                ),
              ),
            ),
            barGroups: values.indexed.map((entry) {
              final (index, value) = entry;
              return BarChartGroupData(
                x: index,
                barRods: [
                  BarChartRodData(
                    toY: value,
                    color: color,
                    width: 21,
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(5),
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
          duration: const Duration(milliseconds: 350),
        ),
      ),
    );
  }
}
