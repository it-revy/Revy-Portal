import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, Bell, ChevronDown, Menu, User, ArrowLeft, LayoutGrid } from 'lucide-react';
import Breadcrumb from './Breadcrumb';

const Header = ({ onToggleMobile, sidebarCollapsed, onToggleCollapse }) => {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) return null;

  const primaryRole = user.roles && user.roles.length > 0
    ? user.roles[0].replace(/_/g, ' ')
    : null;

  const handleToggle = () => {
    if (window.innerWidth <= 768) {
      if (onToggleMobile) onToggleMobile();
    } else {
      if (onToggleCollapse) onToggleCollapse();
    }
  };

  return (
    <header className="header">
      <div className="header-left">
        <button
          className="hamburger-btn"
          onClick={handleToggle}
          title={sidebarCollapsed ? "Expand Sidebar (☰)" : "Collapse Sidebar"}
          aria-label="Toggle navigation menu"
        >
          <Menu size={22} />
        </button>

        <Link
          to="/portal"
          className="portal-back-btn"
          title="Return to REVY Central Services Portal"
        >
          <ArrowLeft size={15} />
          <span>Services</span>
        </Link>

        <div className="header-breadcrumb-wrap desktop-only" style={{ marginLeft: '0.5rem' }}>
          <Breadcrumb />
        </div>
      </div>

      <div className="header-right">
        {/* Notification Bell */}
        <button
          className="header-icon-btn"
          title="Notifications"
          aria-label="View notifications"
        >
          <Bell size={18} />
        </button>

        {/* User Profile Dropdown */}
        <div className="header-profile-dropdown" ref={dropdownRef}>
          <button
            className="header-profile-trigger"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            aria-expanded={dropdownOpen}
            aria-haspopup="true"
            aria-label="User profile options"
          >
            <div className="header-avatar">
              {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="header-user-meta">
              <span className="header-user-name">{user.name}</span>
              <span className="header-user-empid">
                {primaryRole ? `${primaryRole} • ` : ''}{user.employeeId}
              </span>
            </div>
            <ChevronDown size={14} className={`header-chevron ${dropdownOpen ? 'open' : ''}`} />
          </button>

          {dropdownOpen && (
            <div className="header-dropdown-menu">
              <div className="dropdown-user-header">
                <div className="dropdown-avatar-sm">
                  {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                </div>
                <div className="dropdown-user-details">
                  <strong className="dropdown-name">{user.name}</strong>
                  {primaryRole && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', fontWeight: 600, textTransform: 'uppercase' }}>
                      Role: {primaryRole}
                    </span>
                  )}
                  {user.username && <span className="dropdown-username">@{user.username}</span>}
                  <span className="dropdown-empid">{user.employeeId}</span>
                  {user.email && <span className="dropdown-email">{user.email}</span>}
                </div>
              </div>

              <div className="dropdown-actions">
                <button
                  onClick={logout}
                  className="dropdown-logout-item"
                >
                  <LogOut size={16} />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
