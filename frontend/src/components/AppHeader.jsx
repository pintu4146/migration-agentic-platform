import { 
  Header, 
  HeaderName, 
  HeaderNavigation, 
  HeaderMenuItem,
  HeaderGlobalBar,
  HeaderGlobalAction
} from '@carbon/react';
import { Notification, UserAvatar } from '@carbon/icons-react';
import { useNavigate, useLocation } from 'react-router-dom';

const AppHeader = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <Header aria-label="Migration Copilot">
      <HeaderName href="#" prefix="IBM">
        Migration Copilot
      </HeaderName>
      <HeaderNavigation aria-label="Migration Copilot">
        <HeaderMenuItem 
          onClick={() => navigate('/dashboard')}
          isActive={isActive('/dashboard')}
        >
          Dashboard
        </HeaderMenuItem>
        <HeaderMenuItem 
          onClick={() => navigate('/upload')}
          isActive={isActive('/upload')}
        >
          Upload Documents
        </HeaderMenuItem>
      </HeaderNavigation>
      <HeaderGlobalBar>
        <HeaderGlobalAction 
          aria-label="Notifications"
          tooltipAlignment="end"
        >
          <Notification size={20} />
        </HeaderGlobalAction>
        <HeaderGlobalAction 
          aria-label="User Profile"
          tooltipAlignment="end"
        >
          <UserAvatar size={20} />
        </HeaderGlobalAction>
      </HeaderGlobalBar>
    </Header>
  );
};

export default AppHeader;

// Made with Bob
