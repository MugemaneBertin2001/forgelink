import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/services/assets_service.dart';
import '../../../../core/config/router.dart';

class AssetsScreen extends ConsumerStatefulWidget {
  const AssetsScreen({super.key});

  @override
  ConsumerState<AssetsScreen> createState() => _AssetsScreenState();
}

class _AssetsScreenState extends ConsumerState<AssetsScreen> {
  String? _selectedArea;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(assetsProvider.notifier).fetchPlantHierarchy('steel-plant-kigali');
      ref.read(assetsProvider.notifier).fetchStatusSummary();
    });
  }

  @override
  Widget build(BuildContext context) {
    final assetsState = ref.watch(assetsProvider);
    final statusSummary = ref.watch(deviceStatusSummaryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Assets'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () => _showSearchDialog(),
          ),
        ],
      ),
      body: Column(
        children: [
          // Status summary bar
          _StatusSummaryBar(summary: statusSummary),

          // Area filter chips
          _AreaFilterChips(
            areas: assetsState.areas,
            selectedArea: _selectedArea,
            onSelected: (area) => setState(() => _selectedArea = area),
          ),

          // Asset hierarchy
          Expanded(
            child: assetsState.isLoading && assetsState.areas.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : assetsState.error != null && assetsState.areas.isEmpty
                    ? _ErrorView(
                        error: assetsState.error!,
                        onRetry: () => ref.read(assetsProvider.notifier)
                            .fetchPlantHierarchy('steel-plant-kigali'),
                      )
                    : RefreshIndicator(
                        onRefresh: () async {
                          await ref.read(assetsProvider.notifier)
                              .fetchPlantHierarchy('steel-plant-kigali');
                          await ref.read(assetsProvider.notifier).fetchStatusSummary();
                        },
                        child: _AssetHierarchy(
                          areas: assetsState.areas,
                          selectedArea: _selectedArea,
                          searchQuery: _searchQuery,
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  void _showSearchDialog() {
    showDialog(
      context: context,
      builder: (context) {
        final controller = TextEditingController(text: _searchQuery);
        return AlertDialog(
          title: const Text('Search Devices'),
          content: TextField(
            controller: controller,
            autofocus: true,
            decoration: const InputDecoration(
              hintText: 'Enter device name or ID...',
              prefixIcon: Icon(Icons.search),
            ),
            onSubmitted: (value) {
              setState(() => _searchQuery = value);
              Navigator.pop(context);
              if (value.isNotEmpty) {
                ref.read(assetsProvider.notifier).searchDevices(value);
              }
            },
          ),
          actions: [
            TextButton(
              onPressed: () {
                setState(() => _searchQuery = '');
                ref.read(assetsProvider.notifier)
                    .fetchPlantHierarchy('steel-plant-kigali');
                Navigator.pop(context);
              },
              child: const Text('Clear'),
            ),
            ElevatedButton(
              onPressed: () {
                setState(() => _searchQuery = controller.text);
                Navigator.pop(context);
                if (controller.text.isNotEmpty) {
                  ref.read(assetsProvider.notifier).searchDevices(controller.text);
                }
              },
              child: const Text('Search'),
            ),
          ],
        );
      },
    );
  }
}

class _StatusSummaryBar extends StatelessWidget {
  final DeviceStatusSummary summary;

  const _StatusSummaryBar({required this.summary});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: AppColors.surface,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _StatusItem(
            label: 'Total',
            value: summary.total.toString(),
            color: AppColors.primary,
          ),
          _StatusItem(
            label: 'Online',
            value: summary.online.toString(),
            color: AppColors.success,
          ),
          _StatusItem(
            label: 'Offline',
            value: summary.offline.toString(),
            color: AppColors.textSecondary,
          ),
          _StatusItem(
            label: 'Fault',
            value: summary.fault.toString(),
            color: AppColors.critical,
          ),
        ],
      ),
    );
  }
}

class _StatusItem extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatusItem({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: AppTypography.headline3.copyWith(color: color),
        ),
        Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: AppColors.critical.withOpacity(0.5)),
          const SizedBox(height: 16),
          Text(error, style: AppTypography.body2.copyWith(color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}

class _AreaFilterChips extends StatelessWidget {
  final List<Area> areas;
  final String? selectedArea;
  final Function(String?) onSelected;

  const _AreaFilterChips({
    required this.areas,
    required this.selectedArea,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.all(8),
      child: Row(
        children: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: const Text('All'),
              selected: selectedArea == null,
              onSelected: (_) => onSelected(null),
              selectedColor: AppColors.primary.withOpacity(0.2),
              checkmarkColor: AppColors.primary,
            ),
          ),
          ...areas.map((area) {
            final isSelected = selectedArea == area.name;
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilterChip(
                label: Text(area.name),
                selected: isSelected,
                onSelected: (_) => onSelected(area.name),
                selectedColor: AppColors.primary.withOpacity(0.2),
                checkmarkColor: AppColors.primary,
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _AssetHierarchy extends StatelessWidget {
  final List<Area> areas;
  final String? selectedArea;
  final String searchQuery;

  const _AssetHierarchy({
    required this.areas,
    this.selectedArea,
    this.searchQuery = '',
  });

  @override
  Widget build(BuildContext context) {
    final filteredAreas = selectedArea != null
        ? areas.where((a) => a.name == selectedArea).toList()
        : areas;

    if (filteredAreas.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.inventory_2_outlined, size: 64, color: AppColors.textSecondary.withOpacity(0.5)),
            const SizedBox(height: 16),
            Text(
              'No assets found',
              style: AppTypography.subtitle1.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      itemCount: filteredAreas.length,
      itemBuilder: (context, index) {
        final area = filteredAreas[index];
        return _AreaExpansionTile(area: area, searchQuery: searchQuery);
      },
    );
  }
}

class _AreaExpansionTile extends StatelessWidget {
  final Area area;
  final String searchQuery;

  const _AreaExpansionTile({required this.area, this.searchQuery = ''});

  @override
  Widget build(BuildContext context) {
    final deviceCount = _countDevices(area);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ExpansionTile(
        leading: const Icon(Icons.location_on, color: AppColors.primary),
        title: Text(area.name, style: AppTypography.subtitle1),
        subtitle: Row(
          children: [
            Text(
              '$deviceCount devices',
              style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
            ),
            if (area.areaType != 'primary') ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  area.areaType,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.primary,
                    fontSize: 10,
                  ),
                ),
              ),
            ],
          ],
        ),
        children: area.lines.map<Widget>((line) => _LineExpansionTile(
          line: line,
          searchQuery: searchQuery,
        )).toList(),
      ),
    );
  }

  int _countDevices(Area area) {
    int count = 0;
    for (final line in area.lines) {
      for (final cell in line.cells) {
        count += cell.devices.length;
      }
    }
    return count;
  }
}

class _LineExpansionTile extends StatelessWidget {
  final Line line;
  final String searchQuery;

  const _LineExpansionTile({required this.line, this.searchQuery = ''});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 16),
      child: ExpansionTile(
        leading: const Icon(Icons.precision_manufacturing, size: 20),
        title: Text(line.name, style: AppTypography.body2),
        children: line.cells.map<Widget>((cell) => _CellTile(
          cell: cell,
          searchQuery: searchQuery,
        )).toList(),
      ),
    );
  }
}

class _CellTile extends StatelessWidget {
  final Cell cell;
  final String searchQuery;

  const _CellTile({required this.cell, this.searchQuery = ''});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 32),
      child: ExpansionTile(
        leading: const Icon(Icons.category, size: 18),
        title: Text(cell.name, style: AppTypography.body2),
        children: cell.devices.map<Widget>((device) => _DeviceTile(
          device: device,
          isHighlighted: searchQuery.isNotEmpty &&
              (device.name.toLowerCase().contains(searchQuery.toLowerCase()) ||
               device.deviceId.toLowerCase().contains(searchQuery.toLowerCase())),
        )).toList(),
      ),
    );
  }
}

class _DeviceTile extends ConsumerWidget {
  final Device device;
  final bool isHighlighted;

  const _DeviceTile({required this.device, this.isHighlighted = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final color = device.hasFault
        ? AppColors.critical
        : device.isOnline
            ? AppColors.success
            : AppColors.textSecondary;

    return Container(
      color: isHighlighted ? AppColors.warning.withOpacity(0.1) : null,
      child: ListTile(
        contentPadding: const EdgeInsets.only(left: 64, right: 16),
        leading: Icon(Icons.sensors, size: 18, color: color),
        title: Text(device.name, style: AppTypography.caption),
        subtitle: Row(
          children: [
            Text(
              device.deviceId,
              style: AppTypography.caption.copyWith(
                color: AppColors.textSecondary,
                fontFamily: 'monospace',
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                device.status.toUpperCase(),
                style: AppTypography.caption.copyWith(
                  color: color,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (device.unit.isNotEmpty)
              Text(
                device.unit,
                style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
              ),
            const SizedBox(width: 8),
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
        onTap: () => _showDeviceDetail(context, device),
      ),
    );
  }

  void _showDeviceDetail(BuildContext context, Device device) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: Text(device.name, style: AppTypography.headline3),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: (device.hasFault
                          ? AppColors.critical
                          : device.isOnline
                              ? AppColors.success
                              : AppColors.textSecondary).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      device.status.toUpperCase(),
                      style: AppTypography.caption.copyWith(
                        color: device.hasFault
                            ? AppColors.critical
                            : device.isOnline
                                ? AppColors.success
                                : AppColors.textSecondary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              _DetailRow('Device ID', device.deviceId),
              _DetailRow('Type', device.deviceType),
              _DetailRow('Unit', device.unit.isNotEmpty ? device.unit : 'N/A'),
              if (device.description != null)
                _DetailRow('Description', device.description!),
              const Divider(),
              Text('Thresholds', style: AppTypography.subtitle1),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: _ThresholdItem(
                      label: 'Warning Low',
                      value: device.warningLow,
                      color: AppColors.warning,
                    ),
                  ),
                  Expanded(
                    child: _ThresholdItem(
                      label: 'Warning High',
                      value: device.warningHigh,
                      color: AppColors.warning,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: _ThresholdItem(
                      label: 'Critical Low',
                      value: device.criticalLow,
                      color: AppColors.critical,
                    ),
                  ),
                  Expanded(
                    child: _ThresholdItem(
                      label: 'Critical High',
                      value: device.criticalHigh,
                      color: AppColors.critical,
                    ),
                  ),
                ],
              ),
              const Divider(),
              if (device.lastSeen != null)
                _DetailRow('Last Seen', device.lastSeen!.toLocal().toString()),
              _DetailRow('Active', device.isActive ? 'Yes' : 'No'),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pop(context);
                    context.go('${AppRoutes.telemetry}?device=${device.deviceId}');
                  },
                  icon: const Icon(Icons.show_chart),
                  label: const Text('View Telemetry'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
            ),
          ),
          Expanded(
            child: Text(value, style: AppTypography.body2),
          ),
        ],
      ),
    );
  }
}

class _ThresholdItem extends StatelessWidget {
  final String label;
  final double? value;
  final Color color;

  const _ThresholdItem({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
        ),
        Text(
          value != null ? value!.toStringAsFixed(1) : 'N/A',
          style: AppTypography.body2.copyWith(
            color: value != null ? color : AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}
