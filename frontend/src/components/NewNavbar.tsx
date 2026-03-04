import { Link, useLocation, useNavigate } from "react-router-dom";

interface User {
  email: string;
}

interface NewNavbarProps {
  user?: User | null;
  onLogin?: (email: string, password: string) => void;
  onLogout?: () => void;
}

const NewNavbar: React.FC<NewNavbarProps> = ({ user, onLogout }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path: string) => location.pathname === path;

  const handleLoginClick = () => {
    navigate("/generate"); // This will trigger the login flow
  };

  const handleLogoutClick = () => {
    if (onLogout) {
      onLogout();
    }
  };

  return (
    <nav className="bg-white shadow-md border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-16 relative">
          {/* Mobile Navigation Links - Left */}
          <div className="flex sm:hidden items-center space-x-2">
            <Link
              to="/"
              className={`px-2 py-1 rounded text-xs font-medium font-quicksand transition-colors ${
                isActive("/")
                  ? "bg-[#358743] text-white"
                  : "text-gray-700 hover:bg-[#f0f9f1] hover:text-[#358743]"
              }`}
            >
              Validate
            </Link>
            <Link
              to="/chat"
              className={`px-2 py-1 rounded text-xs font-medium font-quicksand transition-colors ${
                isActive("/chat")
                  ? "bg-[#358743] text-white"
                  : "text-gray-700 hover:bg-[#f0f9f1] hover:text-[#358743]"
              }`}
            >
              Chat
            </Link>
            <Link
              to="/generate"
              className={`px-2 py-1 rounded text-xs font-medium font-quicksand transition-colors ${
                isActive("/generate")
                  ? "bg-[#358743] text-white"
                  : "text-gray-700 hover:bg-[#f0f9f1] hover:text-[#358743]"
              }`}
            >
              Generate
            </Link>
          </div>

          {/* Desktop Navigation Links - Center */}
          <div className="hidden sm:flex items-center space-x-4 lg:space-x-8 absolute left-1/2 transform -translate-x-1/2">
            <Link
              to="/"
              className={`px-3 py-2 rounded-md text-xs sm:text-sm font-medium font-quicksand transition-colors ${
                isActive("/")
                  ? "bg-[#358743] text-white"
                  : "text-gray-700 hover:bg-[#f0f9f1] hover:text-[#358743]"
              }`}
            >
              Validation
            </Link>
            <Link
              to="/chat"
              className={`px-3 py-2 rounded-md text-xs sm:text-sm font-medium font-quicksand transition-colors ${
                isActive("/chat")
                  ? "bg-[#358743] text-white"
                  : "text-gray-700 hover:bg-[#f0f9f1] hover:text-[#358743]"
              }`}
            >
              Assistance
            </Link>
            <Link
              to="/generate"
              className={`px-3 py-2 rounded-md text-xs sm:text-sm font-medium font-quicksand transition-colors ${
                isActive("/generate")
                  ? "bg-[#358743] text-white"
                  : "text-gray-700 hover:bg-[#f0f9f1] hover:text-[#358743]"
              }`}
            >
              Generation
            </Link>
          </div>

          {/* Login/Logout Button - Right Side */}
          <div className="ml-auto flex-shrink-0">
            {user ? (
              <div className="flex items-center space-x-3">
                <span className="hidden sm:block text-xs sm:text-sm text-gray-600 font-quicksand">
                  {user.email}
                </span>
                <button
                  onClick={handleLogoutClick}
                  className="inline-flex items-center px-3 py-2 text-xs sm:text-sm font-medium font-quicksand bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors"
                >
                  <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span className="hidden sm:inline">Logout</span>
                  <span className="sm:hidden">Out</span>
                </button>
              </div>
            ) : (
              <button
                onClick={handleLoginClick}
                className="inline-flex items-center px-3 py-2 text-xs sm:text-sm font-medium font-quicksand bg-[#358743] text-white rounded-md hover:bg-[#2d6e36] transition-colors"
              >
                <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                </svg>
                <span className="hidden sm:inline">Login</span>
                <span className="sm:hidden">In</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default NewNavbar;