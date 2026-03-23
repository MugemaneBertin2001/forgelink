import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_theme.dart';

class AssetsScreen extends ConsumerStatefulWidget {
  const AssetsScreen({super.key});

  @override
  ConsumerState<AssetsScreen> createState() => _AssetsScreenState();
}

class _AssetsScreenState extends ConsumerState<AssetsScreen> {
  String? _selectedArea;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Assets'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () {
              // TODO: Search assets
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Area filter chips
          _AreaFilterChips(
            selectedArea: _selectedArea,
            onSelected: (area) => setState(() => _selectedArea = area),
          ),

          // Asset hierarchy
          Expanded(
            child: _AssetHierarchy(selectedArea: _selectedArea),
          ),
        ],
      ),
    );
  }
}

class _AreaFilterChips extends StatelessWidget {
  final String? selectedArea;
  final Function(String?) onSelected;

  const _AreaFilterChips({
    required this.selectedArea,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final areas = [
      'All',
      'Melt Shop',
      'Continuous Casting',
      'Rolling Mill',
      'Finishing',
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.all(8),
      child: Row(
        children: areas.map((area) {
          final isSelected = area == 'All'
              ? selectedArea == null
              : selectedArea == area;

          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Text(area),
              selected: isSelected,
              onSelected: (_) {
                onSelected(area == 'All' ? null : area);
              },
              selectedColor: AppColors.primary.withOpacity(0.2),
              checkmarkColor: AppColors.primary,
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _AssetHierarchy extends StatelessWidget {
  final String? selectedArea;

  const _AssetHierarchy({this.selectedArea});

  @override
  Widget build(BuildContext context) {
    // TODO: Fetch from API
    final hierarchy = _getMockHierarchy();

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      itemCount: hierarchy.length,
      itemBuilder: (context, index) {
        final area = hierarchy[index];
        if (selectedArea != null && area['name'] != selectedArea) {
          return const SizedBox.shrink();
        }
        return _AreaExpansionTile(area: area);
      },
    );
  }

  List<Map<String, dynamic>> _getMockHierarchy() {
    return [
      {
        'name': 'Melt Shop',
        'code': 'melt-shop',
        'lines': [
          {
            'name': 'EAF-1',
            'cells': [
              {
                'name': 'Furnace',
                'devices': [
                  {'id': 'temp-sensor-001', 'name': 'Temperature Sensor 1', 'status': 'online'},
                  {'id': 'temp-sensor-002', 'name': 'Temperature Sensor 2', 'status': 'online'},
                  {'id': 'electrode-001', 'name': 'Electrode System', 'status': 'online'},
                ],
              },
            ],
          },
          {
            'name': 'LRF-1',
            'cells': [
              {
                'name': 'Ladle',
                'devices': [
                  {'id': 'temp-sensor-005', 'name': 'Temperature Sensor', 'status': 'online'},
                ],
              },
            ],
          },
        ],
      },
      {
        'name': 'Continuous Casting',
        'code': 'continuous-casting',
        'lines': [
          {
            'name': 'Caster-1',
            'cells': [
              {
                'name': 'Mold',
                'devices': [
                  {'id': 'level-sensor-001', 'name': 'Level Sensor', 'status': 'online'},
                  {'id': 'flow-meter-001', 'name': 'Flow Meter', 'status': 'warning'},
                ],
              },
            ],
          },
        ],
      },
      {
        'name': 'Rolling Mill',
        'code': 'rolling-mill',
        'lines': [
          {
            'name': 'Roughing',
            'cells': [
              {
                'name': 'Stand 1',
                'devices': [
                  {'id': 'vib-sensor-001', 'name': 'Vibration Sensor', 'status': 'online'},
                  {'id': 'force-sensor-001', 'name': 'Force Sensor', 'status': 'online'},
                ],
              },
            ],
          },
          {
            'name': 'Finishing',
            'cells': [
              {
                'name': 'Stand 6',
                'devices': [
                  {'id': 'vib-sensor-007', 'name': 'Vibration Sensor', 'status': 'alert'},
                  {'id': 'temp-sensor-020', 'name': 'Temperature Sensor', 'status': 'online'},
                ],
              },
            ],
          },
        ],
      },
      {
        'name': 'Finishing',
        'code': 'finishing',
        'lines': [
          {
            'name': 'Inspection',
            'cells': [
              {
                'name': 'Station 1',
                'devices': [
                  {'id': 'ultrasonic-001', 'name': 'Ultrasonic Sensor', 'status': 'online'},
                ],
              },
            ],
          },
        ],
      },
    ];
  }
}

class _AreaExpansionTile extends StatelessWidget {
  final Map<String, dynamic> area;

  const _AreaExpansionTile({required this.area});

  @override
  Widget build(BuildContext context) {
    final lines = area['lines'] as List;
    final deviceCount = _countDevices(area);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ExpansionTile(
        leading: const Icon(Icons.location_on, color: AppColors.primary),
        title: Text(area['name'] as String, style: AppTypography.subtitle1),
        subtitle: Text(
          '$deviceCount devices',
          style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
        ),
        children: lines.map<Widget>((line) => _LineExpansionTile(line: line)).toList(),
      ),
    );
  }

  int _countDevices(Map<String, dynamic> area) {
    int count = 0;
    for (final line in area['lines'] as List) {
      for (final cell in line['cells'] as List) {
        count += (cell['devices'] as List).length;
      }
    }
    return count;
  }
}

class _LineExpansionTile extends StatelessWidget {
  final Map<String, dynamic> line;

  const _LineExpansionTile({required this.line});

  @override
  Widget build(BuildContext context) {
    final cells = line['cells'] as List;

    return Padding(
      padding: const EdgeInsets.only(left: 16),
      child: ExpansionTile(
        leading: const Icon(Icons.precision_manufacturing, size: 20),
        title: Text(line['name'] as String, style: AppTypography.body2),
        children: cells.map<Widget>((cell) => _CellTile(cell: cell)).toList(),
      ),
    );
  }
}

class _CellTile extends StatelessWidget {
  final Map<String, dynamic> cell;

  const _CellTile({required this.cell});

  @override
  Widget build(BuildContext context) {
    final devices = cell['devices'] as List;

    return Padding(
      padding: const EdgeInsets.only(left: 32),
      child: ExpansionTile(
        leading: const Icon(Icons.category, size: 18),
        title: Text(cell['name'] as String, style: AppTypography.body2),
        children: devices.map<Widget>((device) => _DeviceTile(device: device)).toList(),
      ),
    );
  }
}

class _DeviceTile extends StatelessWidget {
  final Map<String, dynamic> device;

  const _DeviceTile({required this.device});

  @override
  Widget build(BuildContext context) {
    final status = device['status'] as String;
    final color = status == 'alert'
        ? AppColors.critical
        : status == 'warning'
            ? AppColors.warning
            : AppColors.success;

    return ListTile(
      contentPadding: const EdgeInsets.only(left: 64, right: 16),
      leading: Icon(Icons.sensors, size: 18, color: color),
      title: Text(device['name'] as String, style: AppTypography.caption),
      subtitle: Text(
        device['id'] as String,
        style: AppTypography.caption.copyWith(
          color: AppColors.textSecondary,
          fontFamily: 'monospace',
        ),
      ),
      trailing: Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
        ),
      ),
      onTap: () {
        // TODO: Navigate to device telemetry
      },
    );
  }
}
