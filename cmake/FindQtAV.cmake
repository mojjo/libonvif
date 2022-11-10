# - Try to find the QtAV library
#
# Once done this will define
#
#  QTAV_FOUND        - system has libqtav
#  QTAV_INCLUDE_DIRS - the libqtav include directory
#  QTAV_LIBRARIES    - Link these to use libqtav

#******************************************************************************
#    QtAV:  Multimedia framework based on Qt and FFmpeg
#    Copyright (C) 2012-2016 Wang Bin <wbsecg1@gmail.com>
#   This file is part of QtAV
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#******************************************************************************/

find_package(Qt5 QUIET REQUIRED NO_MODULE COMPONENTS Core)

get_target_property(qmake Qt5::qmake LOCATION)
execute_process(
    COMMAND ${qmake} -query QT_INSTALL_HEADERS
    OUTPUT_VARIABLE QT_INSTALL_HEADERS
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
execute_process(
    COMMAND ${qmake} -query QT_INSTALL_LIBS
    OUTPUT_VARIABLE QT_INSTALL_LIBS
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

find_path(QTAV_INCLUDE_DIR NAMES QtAV.h
    HINTS ${QT_INSTALL_HEADERS}
    PATH_SUFFIXES QtAV
)
find_path(QTAVWIDGETS_INCLUDE_DIR NAMES QtAVWidgets.h
    HINTS ${QT_INSTALL_HEADERS}
    PATH_SUFFIXES QtAVWidgets
)
if(${CMAKE_BUILD_TYPE} MATCHES "Debug")
    find_library(QTAV_LIBRARY NAMES QtAVd QtAVd1
        HINTS ${QT_INSTALL_LIBS}
    )
    find_library(QTAVWIDGETS_LIBRARY NAMES QtAVWidgetsd QtAVWidgetsd1
        HINTS ${QT_INSTALL_LIBS}
    )
else()
    find_library(QTAV_LIBRARY NAMES QtAV QtAV1
        HINTS ${QT_INSTALL_LIBS}
    )
    find_library(QTAVWIDGETS_LIBRARY NAMES QtAVWidgets QtAVWidgets1
        HINTS ${QT_INSTALL_LIBS}
    )
endif()

set(QTAV_INCLUDE_DIRS ${QTAV_INCLUDE_DIR} ${QTAV_INCLUDE_DIR}/..)
set(QTAV_LIBRARIES ${QTAV_LIBRARY})
if(NOT QTAVWIDGETS_INCLUDE_DIR MATCHES "QTAVWIDGETS_INCLUDE_DIR-NOTFOUND")
    set(QTAVWIDGETS_INCLUDE_DIRS ${QTAVWIDGETS_INCLUDE_DIR} ${QTAVWIDGETS_INCLUDE_DIR}/.. ${QTAV_INCLUDE_DIRS})
endif()
if(NOT QTAV_LIBRARIES MATCHES "QTAV_LIBRARIES-NOTFOUND")
    set(QTAVWIDGETS_LIBRARIES ${QTAVWIDGETS_LIBRARY} ${QTAV_LIBRARY})
endif()

find_package(PackageHandleStandardArgs REQUIRED)
find_package_handle_standard_args(QtAV REQUIRED_VARS QTAV_LIBRARIES QTAV_INCLUDE_DIRS)
mark_as_advanced(QTAV_INCLUDE_DIRS QTAV_LIBRARIES QTAVWIDGETS_INCLUDE_DIRS QTAVWIDGETS_LIBRARIES)

message("QtAV_FOUND                 = ${QTAV_FOUND}")
message("QTAV_INCLUDE_DIRS          = ${QTAV_INCLUDE_DIRS}")
message("QTAV_LIBRARIES             = ${QTAV_LIBRARIES}")
message("QTAVWIDGETS_INCLUDE_DIRS   = ${QTAVWIDGETS_INCLUDE_DIRS}")
message("QTAVWIDGETS_LIBRARIES      = ${QTAVWIDGETS_LIBRARIES}")
