import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/services/telemetry_service.dart';
import '../../../../core/services/assets_service.dart';

class TelemetryScreen extends ConsumerStatefulWidget {
  final String? initialDeviceId;

  const TelemetryScreen({super.key, this.initialDeviceId});

  @override
  ConsumerState<TelemetryScreen> createState() => _TelemetryScreenState();
}

class _TelemetryScreenState extends ConsumerState<TelemetryScreen> {
  String _selectedTimeRange = '1h';
  String? _selectedDevice;

  @override
  void initState() {
    super.initState();
    _selectedDevice = widget.initialDeviceId;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Fetch devices for selector
      ref.read(assetsProvider.notifier).fetchDevices();
      // If device pre-selected, fetch its data
      if (_selectedDevice != null) {
        _fetchDeviceData(_selectedDevice!);
      }
    });
  }

  void _fetchDeviceData(String deviceId) {
    final hours = _timeRangeToHours(_selectedTimeRange);
    ref.read(telemetryProvider.notifier).fetchDeviceData(deviceId, hours: hours);
  }

  int _timeRangeToHours(String range) {
    switch (range) {
      case '15m': return 1;
      case '1h': return 1;
      case '6h': return 6;
      case '24h': return 24;
      default: return 1;
    }
  }

  String _timeRangeInterval(String range) {
    switch (range) {
      case '15m': return '1m';
      case '1h': return '1m';
      case '6h': return '5m';
      case '24h': return '15m';
      default: return '1m';
    }
  }

  @override
  Widget build(BuildContext context) {
    final telemetryState = ref.watch(telemetryProvider);
    final devices = ref.watch(devicesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Telemetry'),
        actions: [
          PopupMenuButton<String>(
            initialValue: _selectedTimeRange,
            onSelected: (value) {
              setState(() => _selectedTimeRange = value);
              if (_selectedDevice != null) {
                final hours = _timeRangeToHours(value);
                ref.read(telemetryProvider.notifier).fetchHistory(
                  _selectedDevice!,
                  interval: _timeRangeInterval(value),
                  hours: hours,
                );
              }
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
      body: RefreshIndicator(
        onRefresh: () async {
          if (_selectedDevice != null) {
            _fetchDeviceData(_selectedDevice!);
          }
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Device selector
            _DeviceSelector(
              devices: devices,
              selectedDevice: _selectedDevice,
              onSelected: (device) {
                setState(() => _selectedDevice = device);
                if (device != null) {
                  _fetchDeviceData(device);
                }
              },
            ),
            const SizedBox(height: 16),

            // Loading state
            if (telemetryState.isLoading && _selectedDevice != null)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (telemetryState.error != null && _selectedDevice != null)
              _ErrorCard(
                error: telemetryState.error!,
                onRetry: () => _fetchDeviceData(_selectedDevice!),
              )
            else ...[
              // Current value card
              _CurrentValueCard(
                deviceId: _selectedDevice,
                latestValue: telemetryState.latestValue,
              ),
              const SizedBox(height: 16),

              // Chart
              _TelemetryChart(
                deviceId: _selectedDevice,
                history: telemetryState.history,
                timeRange: _selectedTimeRange,
              ),
              const SizedBox(height: 16),

              // Statistics
              _StatisticsCard(
                deviceId: _selectedDevice,
                stats: telemetryState.stats,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorCard({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: AppColors.critical.withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(Icons.error_outline, color: AppColors.critical),
            const SizedBox(height: 8),
            Text(error, style: AppTypography.body2),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DeviceSelector extends StatelessWidget {
  final List<Device> devices;
  final String? selectedDevice;
  final Function(String?) onSelected;

  const _DeviceSelector({
    required this.devices,
    required this.selectedDevice,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
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
              value: device.deviceId,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(device.name, style: AppTypography.body2),
                  Text(
                    '${device.deviceType} • ${device.deviceId}',
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
  final DeviceLatestValue? latestValue;

  const _CurrentValueCard({this.deviceId, this.latestValue});

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

    if (latestValue == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Center(
            child: Text(
              'No data available',
              style: AppTypography.body2.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ),
      );
    }

    final statusColor = latestValue!.status == 'normal'
        ? AppColors.success
        : latestValue!.status == 'warning'
            ? AppColors.warning
            : AppColors.critical;

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
                        latestValue!.value.toStringAsFixed(1),
                        style: AppTypography.headline1.copyWith(
                          color: statusColor,
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6, left: 4),
                        child: Text(
                          latestValue!.unit,
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
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    latestValue!.status.toUpperCase(),
                    style: AppTypography.caption.copyWith(
                      color: statusColor,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _formatTimestamp(latestValue!.timestamp),
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

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ago';
  }
}

class _TelemetryChart extends StatelessWidget {
  final String? deviceId;
  final List<TelemetryPoint> history;
  final String timeRange;

  const _TelemetryChart({
    this.deviceId,
    required this.history,
    required this.timeRange,
  });

  @override
  Widget build(BuildContext context) {
    if (deviceId == null) return const SizedBox.shrink();

    if (history.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Center(
            child: Text(
              'No historical data available',
              style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
            ),
          ),
        ),
      );
    }

    // Convert history to chart spots
    final spots = <FlSpot>[];
    for (var i = 0; i < history.length; i++) {
      spots.add(FlSpot(i.toDouble(), history[i].value));
    }

    // Calculate min/max for better chart display
    final values = history.map((p) => p.value).toList();
    final minValue = values.reduce((a, b) => a < b ? a : b);
    final maxValue = values.reduce((a, b) => a > b ? a : b);
    final padding = (maxValue - minValue) * 0.1;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('History', style: AppTypography.subtitle1),
                Text(
                  '${history.length} points',
                  style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: (maxValue - minValue) / 4,
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
                          value.toStringAsFixed(0),
                          style: AppTypography.caption,
                        ),
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: (history.length / 5).ceilToDouble(),
                        getTitlesWidget: (value, meta) {
                          final index = value.toInt();
                          if (index < 0 || index >= history.length) return const Text('');
                          final timestamp = history[index].timestamp;
                          return Text(
                            '${timestamp.hour}:${timestamp.minute.toString().padLeft(2, '0')}',
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
                  ],
                  minY: minValue - padding,
                  maxY: maxValue + padding,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _LegendItem(color: AppColors.chartBlue, label: 'Value'),
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
  final DeviceStats? stats;

  const _StatisticsCard({this.deviceId, this.stats});

  @override
  Widget build(BuildContext context) {
    if (deviceId == null) return const SizedBox.shrink();

    if (stats == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Center(
            child: Text(
              'No statistics available',
              style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
            ),
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Statistics', style: AppTypography.subtitle1),
                Text(
                  '${stats!.count} samples',
                  style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _StatItem(label: 'Min', value: stats!.min.toStringAsFixed(1))),
                Expanded(child: _StatItem(label: 'Max', value: stats!.max.toStringAsFixed(1))),
                Expanded(child: _StatItem(label: 'Avg', value: stats!.avg.toStringAsFixed(1))),
                Expanded(child: _StatItem(label: 'Std Dev', value: stats!.stddev.toStringAsFixed(2))),
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
