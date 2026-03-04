import { useState } from "react";
import { Link } from "react-router-dom";

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="bg-white shadow-md h-auto lg:h-44 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col gap-2 lg:gap-4 pt-2 lg:pt-4">
        <div className="text-center hidden lg:block">
          <p className="text-sm lg:text-base font-poppins font-bold text-[#1B5E20] animate-blink tracking-wide">
            Why not take advantage of the immense opportunities.......
          </p>
        </div>
        <div className="flex justify-between items-center h-16 lg:h-28 py-2">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link to="/" className="flex items-center">
              <img
                src="/HCO-Logo.avif"
                alt="HCO - Halal Healthy Hygienic"
                className="h-12 sm:h-16 lg:h-32 w-auto"
              />
            </Link>
          </div>

          {/* Tagline - Centered */}

          {/* Desktop Navigation */}
          <div className="hidden lg:flex font-normal items-center space-x-8">
            <Link
              to="/"
              className="text-gray-800 hover:text-black  text-base transition-colors font-quicksand"
            >
              Home
            </Link>
            <Link
              to="/about"
              className="text-gray-800 hover:text-black  text-base transition-colors font-quicksand"
            >
              About
            </Link>
            <Link
              to="/halal-certification-process"
              className="text-gray-800 hover:text-black  text-base transition-colors font-quicksand"
            >
              Halal Certification Process
            </Link>
            <Link
              to="/policies"
              className="text-gray-800 hover:text-black text-base transition-colors font-quicksand"
            >
              Policies
            </Link>
            <Link
              to="/faq"
              className="text-gray-800 hover:text-black  text-base transition-colors font-quicksand"
            >
              FAQ
            </Link>
            <Link
              to="/contact"
              className="text-gray-800 hover:text-black  text-base transition-colors font-quicksand"
            >
              Contact
            </Link>
            {/* "More" with hover dropdown */}
            <div className="relative group">
              <button className="flex items-center px-2 text-gray-800  text-base font-quicksand transition-colors group-hover:bg-[#75b569] group-hover:text-white h-10 rounded-sm">
                More
                <svg
                  className="ml-1 h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              <div className="absolute left-0 mt-0 w-44 bg-white border border-gray-200 shadow-lg z-50 hidden group-hover:block">
                <div className="py-2">
                  <Link
                    to="/"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Validate
                  </Link>
                  <Link
                    to="/chat"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Chat Assistant
                  </Link>
                  <Link
                    to="/generate"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Generation
                  </Link>
                  <Link
                    to="/register"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Register
                  </Link>
                  <Link
                    to="/services"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Services
                  </Link>
                  <Link
                    to="/news"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    News
                  </Link>
                  <Link
                    to="/blog"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Blog
                  </Link>
                  <Link
                    to="/testimonials"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Testimonials
                  </Link>
                  <Link
                    to="/jobs"
                    className="block px-4 py-2 text-gray-700 hover:bg-[#75b569] hover:text-white font-quicksand"
                  >
                    Jobs
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Contact Info - Right aligned */}
          <div className="hidden lg:block text-right text-lg xl:text-xl font-semibold ">
            <a
              href="mailto:info@hcoltd.co.uk"
              className="block text-[#7c9b78] hover:text-[#5e8159] transition-colors font-quicksand text-sm lg:text-base xl:text-lg"
            >
              info@hcoltd.co.uk
            </a>
            <a
              href="tel:+443335770902"
              className="block font-normal  text-[#7c9b78] hover:text-[#5e8159] transition-colors underline font-quicksand text-sm lg:text-base xl:text-lg"
              style={{ fontFamily: "Quicksand, sans-serif" }}
            >
              +44 (0) 333 577 0902
            </a>
          </div>

          {/* Mobile menu button */}
          <div className="lg:hidden">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:bg-gray-100 focus:outline-none"
            >
              <span className="sr-only">Open main menu</span>
              {!isOpen ? (
                <svg
                  className="block h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              ) : (
                <svg
                  className="block h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <div className="lg:hidden border-t border-gray-200">
          <div className="px-4 pt-4 pb-4 space-y-2 bg-white max-h-screen overflow-y-auto">
            <Link
              to="/"
              className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
              onClick={() => setIsOpen(false)}
            >
              Home
            </Link>
            <Link
              to="/about"
              className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
              onClick={() => setIsOpen(false)}
            >
              About
            </Link>
            <Link
              to="/halal-certification-process"
              className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
              onClick={() => setIsOpen(false)}
            >
              Halal Certification Process
            </Link>
            <Link
              to="/policies"
              className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
              onClick={() => setIsOpen(false)}
            >
              Policies
            </Link>
            <Link
              to="/faq"
              className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
              onClick={() => setIsOpen(false)}
            >
              FAQ
            </Link>
            <Link
              to="/contact"
              className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
              onClick={() => setIsOpen(false)}
            >
              Contact
            </Link>

            {/* Mobile submenu items */}
            <div className="pt-2 border-t border-gray-200 mt-3">
              <Link
                to="/register"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                Register
              </Link>
              <Link
                to="/chat"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                Chat Assistant
              </Link>
              <Link
                to="/generate"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                Generation
              </Link>
              <Link
                to="/services"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                Services
              </Link>
              <Link
                to="/news"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                News
              </Link>
              <Link
                to="/blog"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                Blog
              </Link>
              <Link
                to="/testimonials"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                Testimonials
              </Link>
              <Link
                to="/jobs"
                className="block px-3 py-3 text-gray-700 hover:bg-[#75b569] hover:text-white font-medium font-quicksand rounded-md transition-colors"
                onClick={() => setIsOpen(false)}
              >
                Jobs
              </Link>
            </div>
            <div className="px-3 py-4 border-t border-gray-200 mt-3">
              <div className="text-xs text-gray-400 mb-2 font-quicksand uppercase tracking-wide">Contact</div>
              <a
                href="mailto:info@hcoltd.co.uk"
                className="block text-sm text-[#7c9b78] hover:text-[#5e8159] mb-2 font-quicksand transition-colors"
              >
                📧 info@hcoltd.co.uk
              </a>
              <a
                href="tel:+443335770902"
                className="block text-sm text-[#7c9b78] hover:text-[#5e8159] underline font-quicksand transition-colors"
              >
                📞 +44 (0) 333 577 0902
              </a>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
