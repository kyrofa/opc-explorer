from setuptools import setup


setup(name="opcua-client",
      version="0.8.4",
      description="OPC-UA Client GUI",
      author="Key Technology",
      python_requires='~=3.8.0', # Only expand this as we add tests for them
      url='https://github.com/FreeOpcUa/opcua-client-gui',
      packages=["uaclient", "uaclient.theme"],
      license="GNU General Public License",
      install_requires=["asyncua", "opcua-widgets>=0.6.0", "PyQt5"],
      entry_points={'console_scripts':
                    ['opcua-client = uaclient.mainwindow:main']
                    }
      )
