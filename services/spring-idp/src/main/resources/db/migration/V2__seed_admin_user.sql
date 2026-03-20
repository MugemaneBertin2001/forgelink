-- ForgeLink IDP Schema Migration V2
-- Seed default admin user
-- Password: Admin@ForgeLink2026! (BCrypt hash)

INSERT INTO idp.users (
    id,
    email,
    password_hash,
    first_name,
    last_name,
    plant_id,
    enabled,
    locked
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin@forgelink.local',
    '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qQRvlnPj4S/KGe',
    'System',
    'Administrator',
    'steel-plant-kigali',
    TRUE,
    FALSE
) ON CONFLICT (email) DO NOTHING;

-- Assign FACTORY_ADMIN role
INSERT INTO idp.user_roles (user_id, role)
VALUES ('00000000-0000-0000-0000-000000000001', 'FACTORY_ADMIN')
ON CONFLICT DO NOTHING;

-- Seed demo users for different roles
INSERT INTO idp.users (id, email, password_hash, first_name, last_name, plant_id, enabled, locked)
VALUES
    ('00000000-0000-0000-0000-000000000002', 'operator@forgelink.local',
     '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qQRvlnPj4S/KGe',
     'Plant', 'Operator', 'steel-plant-kigali', TRUE, FALSE),
    ('00000000-0000-0000-0000-000000000003', 'tech@forgelink.local',
     '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qQRvlnPj4S/KGe',
     'Field', 'Technician', 'steel-plant-kigali', TRUE, FALSE),
    ('00000000-0000-0000-0000-000000000004', 'viewer@forgelink.local',
     '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qQRvlnPj4S/KGe',
     'Dashboard', 'Viewer', 'steel-plant-kigali', TRUE, FALSE)
ON CONFLICT (email) DO NOTHING;

-- Assign roles
INSERT INTO idp.user_roles (user_id, role)
VALUES
    ('00000000-0000-0000-0000-000000000002', 'PLANT_OPERATOR'),
    ('00000000-0000-0000-0000-000000000003', 'TECHNICIAN'),
    ('00000000-0000-0000-0000-000000000004', 'VIEWER')
ON CONFLICT DO NOTHING;
