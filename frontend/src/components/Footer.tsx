const Footer = () => {
  return (
    <footer className="bg-[#3a8f43] py-6 lg:py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center space-y-4 lg:space-y-6">
          {/* Logo Section */}
          <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-6 lg:space-x-8">
            {/* First Logo */}
            <div className="bg-white rounded-lg p-2 lg:p-3 shadow-md">
              <img 
                src="/footer/HCO-logo.avif" 
                alt="HCO - Halal Healthy Hygienic"
                className="h-12 sm:h-16 lg:h-20 w-auto"
              />
            </div>

            {/* Second Logo */}
            <div className="bg-white rounded-lg p-2 lg:p-3 shadow-md">
              <img 
                src="/footer/logo-2.avif" 
                alt="HCO Halal Certification Organisation"
                className="h-12 sm:h-16 lg:h-20 w-auto"
              />
            </div>
          </div>

          {/* Copyright Text */}
          <div className="text-white text-center px-4">
            <p className="text-xs sm:text-sm lg:text-base font-quicksand">
              © 2016 Halal Certification Organisation Ltd
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;