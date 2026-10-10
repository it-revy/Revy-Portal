import {
  Utensils,
  LayoutDashboard,
  CalendarCheck,
  ShoppingBag,
  ListOrdered,
  Wallet,
  Landmark,
  Users,
  CalendarRange,
  FileSpreadsheet,
  PieChart,
  ShieldAlert,
  Settings
} from 'lucide-react';

export const BMS_NAV_ITEMS = [
  {
    path: '/bms/response',
    legacyPaths: ['/today', '/response', '/breakfast-response'],
    label: "Today's Entry",
    icon: Utensils,
    permission: 'breakfast.submit',
    orPermission: 'breakfast.view'
  },
  {
    path: '/bms/dashboard',
    legacyPaths: ['/admin/dashboard'],
    label: 'Dashboard',
    icon: LayoutDashboard,
    permission: 'breakfast.view'
  },
  {
    path: '/bms/daily-entry',
    legacyPaths: ['/admin/daily-entry'],
    label: 'Daily Entry',
    icon: CalendarCheck,
    permission: 'breakfast.view'
  },
  {
    path: '/bms/orders',
    legacyPaths: ['/admin/orders'],
    label: 'Orders',
    icon: ListOrdered,
    permission: 'breakfast.orders.view'
  },
  {
    path: '/bms/additional-orders',
    legacyPaths: ['/admin/additional-orders'],
    label: 'Additional Orders',
    icon: ShoppingBag,
    permission: 'breakfast.view'
  },
  {
    path: '/bms/money',
    legacyPaths: ['/admin/breakfast-money'],
    label: 'Breakfast Ledger',
    icon: Wallet,
    permission: 'breakfast.money.view'
  },
  {
    path: '/bms/finance',
    legacyPaths: ['/finance/fund-requests'],
    label: 'Finance Approvals',
    icon: Landmark,
    permission: 'finance.breakfast_fund.view'
  },
  {
    path: '/bms/employees',
    legacyPaths: ['/employees'],
    label: 'Employees',
    icon: Users,
    permission: 'breakfast.view'
  },
  {
    path: '/bms/holidays',
    legacyPaths: ['/admin/holidays'],
    label: 'Public Holidays',
    icon: CalendarRange,
    permission: 'breakfast.view'
  },
  {
    path: '/bms/reports',
    legacyPaths: ['/reports'],
    label: 'Reports',
    icon: FileSpreadsheet,
    permission: 'breakfast.report'
  },
  {
    path: '/bms/ceo-view',
    legacyPaths: ['/ceo-dashboard'],
    label: 'CEO Insights',
    icon: PieChart,
    role: 'CEO'
  },
  {
    path: '/bms/audit-logs',
    legacyPaths: ['/audit-logs'],
    label: 'Audit Trail',
    icon: ShieldAlert,
    permission: 'breakfast.view'
  },
  {
    path: '/bms/settings',
    legacyPaths: ['/settings'],
    label: 'Settings',
    icon: Settings,
    permission: 'breakfast.view'
  }
];

export default BMS_NAV_ITEMS;
