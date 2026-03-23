import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../../../core/theme/app_theme.dart';

class TelemetryScreen extends ConsumerStatefulWidget {
  const TelemetryScreen({super.key});

  @override
  ConsumerState<TelemetryScreen> createState() => _TelemetryScreenState();
}

class _TelemetryScreenState extends ConsumerState<TelemetryScreen> {
  String _selectedTimeRange = '1h';
  String? _selectedDevice;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Telemetry'),
        actions: [
          PopupMenuButton<String>(
            initialValue: _selectedTimeRange,
            onSelected: (value) {
              setState(() => _selectedTimeRange = value);
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: '15m', child: Text('Last 15 min')),
              const PopupMenuItem(value: '1h', child: Text('Last 1 hour')),
              const PopupMenuItem(value: '6h', child: Text('Last 6 hours')),
              const PopupMenuItem(value: '24h', child: Text('Last 24 hours')),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  const Icon(Icons.schedule),
                  const SizedBox(width: 4),
                  Text(_selectedTimeRange),
                ],
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Device selector
          _DeviceSelector(
            selectedDevice: _selectedDevice,
            onSelected: (device) => setState(() => _selectedDevice = device),
          ),
          const SizedBox(height: 16),

          // Current value card
          _CurrentValueCard(deviceId: _selectedDevice),
          const SizedBox(height: 16),

          // Chart
          _TelemetryChart(
            deviceId: _selectedDevice,
            timeRange: _selectedTimeRange,
          ),
          const SizedBox(height: 16),

          // Statistics
          _StatisticsCard(deviceId: _selectedDevice),
        ],
      ),
    );
  }
}

class _DeviceSelector extends StatelessWidget {
  final String? selectedDevice;
  final Function(String?) onSelected;

  const _DeviceSelector({
    required this.selectedDevice,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    // TODO: Fetch from API
    final devices = [
      {'id': 'temp-sensor-001', 'name': 'EAF-1 Temperature', 'area': 'Melt Shop'},
      {'id': 'temp-sensor-002', 'name': 'LRF-1 Temperature', 'area': 'Melt Shop'},
      {'id': 'flow-meter-001', 'name': 'Cooling Flow', 'area': 'Casting'},
      {'id': 'vib-sensor-007', 'name': 'Stand 6 Vibration', 'area': 'Rolling Mill'},
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: DropdownButtonFormField<String>(
          value: selectedDevice,
          decoration: const InputDecoration(
            labelText: 'Select Device',
            prefixIcon: Icon(Icons.sensors),
            border: InputBorder.none,
          ),
          items: devices.map((device) {
            return DropdownMenuItem(
              value: device['id'],
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(device['name']!, style: AppTypography.body2),
                  Text(
                    '${device['area']} • ${device['id']}',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
          onChanged: onSelected,
          isExpanded: true,
        ),
      ),
    );
  }
}

class _CurrentValueCard extends StatelessWidget {
  final String? deviceId;

  const _CurrentValueCard({this.deviceId});

  @override
  Widget build(BuildContext context) {
    if (deviceId == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Center(
            child: Text(
              'Select a device to view telemetry',
              style: AppTypography.body2.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ),
      );
    }

    // TODO: Fetch from API
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Current Value',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '1,642',
                        style: AppTypography.headline1.copyWith(
                          color: AppColors.primary,
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6, left: 4),
                        child: Text(
                          '°C',
                          style: AppTypography.body1.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Row(
                  children: [
                    const Icon(Icons.trending_up, color: AppColors.warning, size: 16),
                    const SizedBox(width: 4),
                    Text(
                      '+2.3%',
                      style: AppTypography.body2.copyWith(color: AppColors.warning),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'vs 5 min ago',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _TelemetryChart extends StatelessWidget {
  final String? deviceId;
  final String timeRange;

  const _TelemetryChart({this.deviceId, required this.timeRange});

  @override
  Widget build(BuildContext context) {
    if (deviceId == null) return const SizedBox.shrink();

    // TODO: Fetch from API
    final spots = List.generate(20, (i) {
      return FlSpot(i.toDouble(), 1620 + (i % 5) * 10 + (i * 2) % 20);
    });

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Temperature History', style: AppTypography.subtitle1),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: 20,
                    getDrawingHorizontalLine: (value) => FlLine(
                      color: Colors.grey.shade200,
                      strokeWidth: 1,
                    ),
                  ),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 50,
                        getTitlesWidget: (value, meta) => Text(
                          '${value.toInt()}°',
                          style: AppTypography.caption,
                        ),
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          if (value.toInt() % 5 != 0) return const Text('');
                          return Text(
                            '${value.toInt()}m',
                            style: AppTypography.caption,
                          );
                        },
                      ),
                    ),
                    rightTitles: const AxisTitles(),
                    topTitles: const AxisTitles(),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: AppColors.chartBlue,
                      barWidth: 2,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        color: AppColors.chartBlue.withOpacity(0.1),
                      ),
                    ),
                    // Threshold line
                    LineChartBarData(
                      spots: List.generate(20, (i) => FlSpot(i.toDouble(), 1650)),
                      isCurved: false,
                      color: AppColors.warning,
                      barWidth: 1,
                      dotData: const FlDotData(show: false),
                      dashArray: [5, 5],
                    ),
                  ],
                  minY: 1600,
                  maxY: 1680,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _LegendItem(color: AppColors.chartBlue, label: 'Value'),
                const SizedBox(width: 16),
                _LegendItem(color: AppColors.warning, label: 'Threshold'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 3,
          color: color,
        ),
        const SizedBox(width: 4),
        Text(label, style: AppTypography.caption),
      ],
    );
  }
}

class _StatisticsCard extends StatelessWidget {
  final String? deviceId;

  const _StatisticsCard({this.deviceId});

  @override
  Widget build(BuildContext context) {
    if (deviceId == null) return const SizedBox.shrink();

    // TODO: Fetch from API
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Statistics', style: AppTypography.subtitle1),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _StatItem(label: 'Min', value: '1,605°C')),
                Expanded(child: _StatItem(label: 'Max', value: '1,678°C')),
                Expanded(child: _StatItem(label: 'Avg', value: '1,638°C')),
                Expanded(child: _StatItem(label: 'Std Dev', value: '12.4')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;

  const _StatItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: AppTypography.subtitle1.copyWith(color: AppColors.primary),
        ),
        Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }
}
