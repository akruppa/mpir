'''
Set up Visual Sudio 2010 to build a specified MPIR configuration

Copyright (C) 2011, Brian Gladman

32-bit:
x86w:  x86, i386, i486, i586, pentium, pentiummmx, k6, k62, k63, k7, athlon, viac3, viac32, x86_64
p6:    pentiumpro, i686
mmx:   pentium2
sse2:  pentium4, prescott, core, netburst, netburstlahf
p3mmx: pentium3, k8, k10, k102, k103, bulldozer, bobcat, core2, penryn, nehalem, westmere, sandybridge, atom, nano

64-bit:
x86_64:       x86_64w
netburst:     netburst, netburstlahf
k8only:       k8, nano
k10:          k10
k102:         k102, k103, bulldozer
bobcat:       bobcat
core2:        core2
penryn:       penryn
nehalem:      nehalem
westmere:     westmere
sandybridge:  sandybridge
atom          atom
'''

from __future__ import print_function
from operator import itemgetter
from os import listdir, walk, unlink, makedirs
from os.path import split, splitext, isdir, relpath, join, exists
from copy import deepcopy
from sys import exit
from filecmp import cmp
from shutil import copy
from re import search

is_DLL = False
is_debug = False

lib_type = 'dll' if is_DLL else 'lib'

# The path to the mpir root directory
mpir_dir = 'C:/Users/Brian Gladman/Documents/Visual Studio 2010/Projects/mpir/'
vc10_dir = mpir_dir + 'build.vc10/'
out_dir = vc10_dir + 'dll/' if is_DLL else 'lib/' 

# paths that might incsrc_listude source filesv(*.c, *.h, *.asm)
c_directories  = ( '', 'build.vc10', 'mpf', 'mpq', 'mpz', 'printf', 'scanf' )

# files that are to be excluded from the build
exclude_file_list = ('config.guess', 'cfg', 'getopt', 'getrusage', 'gettimeofday', 'cpuid',
                     'obsolete', 'win_timing', 'gmp-mparam', 'tal-debug', 'tal-notreent',
                     'new_fft', 'new_fft_with_flint', 'compat', 'udiv_w_sdiv' )

# copy from file ipath to file opath but avoid copying if 
# opath exists and is the same as ipath (this is to avoid
# triggering an unecessary rebuild).

def write_f(ipath, opath):
  if exists(ipath) and not isdir(ipath):
    if exists(opath):
      if isdir(opath) or cmp(ipath, opath):
        return
    copy(ipath, opath)
    
# append a file (ipath) to an existing file (opath) 

def append_f(ipath, opath):
  try:
    with open(opath, 'ab') as out_file:
      try:
        with open(ipath, 'rb') as in_file:
          buf = in_file.read(8192)
          while buf:
            out_file.write(buf)
            buf = in_file.read(8192)          
      except IOError:
        print('error reading {0:s} for input'.format(f))
        return
  except IOError:
    print('error opening {0:s} for output'.format(opath))

# copy files in a list from in_dir to out_dir
def copy_files(file_list, in_dir, out_dir):
  makedirs(out_dir, exist_ok=True)
  for f in file_list:
    copy(join(in_dir, f), out_dir)
    
# Recursively search a given directory tree to find header, 
# C and assembler code files that either replace or augment
# the generic C source files in the input list 'cf_list'. 
# As the directory tree is searched, files in each directory
# become the source code files for the current directory and
# the default source code files for its child directories. 
#
# Lists of default header, C and assembler source code files
# are maintained as the tree is traversed and if a file in
# the current directory matches the name of a file in the 
# default file list (name matches ignore file extensions), 
# the name in the list is removed and is replaced by the new
# file found. On return each directory in the tree had an
# entry in the returned dictionary that contains:
#
# 1. The list of header files
#
# 2. The list of C source code files for the directory 
#
# 3. The list of assembler code files that replace C files
#
# 4. The list of assembler files that are not C replacements
#

def find_asm(path, cf_list):  
  d = dict()
  for root, dirs, files in walk(path):
    if '.svn' in dirs:                  # ignore SVN directories
      dirs.remove('.svn')
    relp = relpath(root, path)          # path from asm root
    relr = relpath(root, mpir_dir)      # path from MPIR root    
    if relp == '.':                     # set C files as default
      relp = h = t = ''
      d[''] = [ [], deepcopy(cf_list), [], [] ]
    else:
      h, t = split(relp)                # h = parent, t = this directory
      hh, h = split(h)
      # copy defaults from this directories parent
      d[t] = [ deepcopy(d[h][0]), deepcopy(d[h][1]), 
               deepcopy(d[h][2]), deepcopy(d[h][3]) ]
    for f in files:                     # for the files in this directory
      n, x = splitext(f)
      if x == '.h':                     # if it is a header file, remove
        for cf in reversed(d[t][0]):    # any matching default
          if cf[0] == n:
            d[t][0].remove(cf)
        d[t][0] += [(n, x, relr)]       # and add the local header file
      if x == '.c':                     # if it is a C file, remove
        for cf in reversed(d[t][1]):    # any matching default
          if cf[0] == n:
            d[t][1].remove(cf)
        d[t][1] += [(n, x, relr)]       # and add the local C file
      if x == '.asm':                   # if it is an assembler file
        match = False
        for cf in reversed(d[t][1]):    # remove any matching C file
          if cf[0] == n:
            d[t][1].remove(cf)
            match = True
            break
        for cf in reversed(d[t][2]):    # and remove any matching
          if cf[0] == n:                # assembler file
            d[t][2].remove(cf)
            match = True
            break
        if match:                       # if a match was found, put the 
          d[t][2] += [(n, x, relr)]     # file in the replacement list
        else:                           # otherwise look for it in the
          for cf in reversed(d[t][3]):  # additional files list
            if cf[0] == n:         
              d[t][3].remove(cf)
              break
          d[t][3] += [(n, x, relr)]
  for k in d:                           # additional assembler list
    for i in range(4):
      d[k][i].sort(key=itemgetter(0))   # sort the four file lists
  return d

# create 4 lists of c, h, cc (or cpp) and asm (or as) in a directory

def find_src(dir_list):
  # list number from file extension
  di = { '.h': 0, '.c': 1, '.cc': 2, '.cpp': 2, '.asm': 3, '.as': 3 }
  list = [ [], [], [], [] ]
  for d in dir_list:
    for f in listdir(join(mpir_dir, d)):
      if f == '.svn':
        continue                        # ignore SVN directories
      if not isdir(f):
        n, x = splitext(f)              # split into name + extension
        if x in di and not n in exclude_file_list:
          list[di[x]] += [(n, x, d)]    # if of the right type and is
  for x in list:                        # not in the exclude list 
    x.sort(key=itemgetter(2, 0, 1))     # add it to appropriaate list
  return list

# generate VIsual Studio 2010 IDE Filter

def filter_folders(cf_list, af_list, outf):
  
  f1 = r'''  <ItemGroup>
    <Filter Include="Header Files" />
    <Filter Include="Source Files" />
'''
  f2 = r'''    <Filter Include="Source Files\{0:s}" />
'''  
  f3 = r'''  </ItemGroup>
'''  
  c_dirs = set(i[2] for i in cf_list)
  a_dirs = set(i[2] for i in af_list)
  if a_dirs:
    c_dirs |= set(('mpn\yasm',))
  outf.write(f1)
  for d in sorted(c_dirs):
    if d:
      t = d if d != 'mpn\generic' else 'mpn'
      outf.write(f2.format(t))
  outf.write(f3)

filter_hdr_item = '    <ClInclude Include="..\..\{}">\n      <Filter>Header Files</Filter>\n    </ClInclude>\n'

def filter_headers(hdr_list, outf):
  
  f1 = r'''  <ItemGroup>
'''
  f2 = r'''    <ClInclude Include="..\..\{}">
      <Filter>Header Files</Filter>
    </ClInclude>
'''
  f3 = r'''  </ItemGroup>
'''
  outf.write(f1)
  for h in hdr_list:
    outf.write(f2.format(h))
  outf.write(f3)

def filter_csrc(cf_list, outf):
  
  f1 = r'''  <ItemGroup>
'''
  f2 = r'''  <ClCompile Include="..\..\{1:s}\{0:s}">
    <Filter>Source Files\{2:s}</Filter>
  </ClCompile>
'''
  f3 = r'''  </ItemGroup>
'''
  outf.write(f1)
  for i in cf_list:
    t = 'mpn' if i[2].endswith('generic') else i[2]
    outf.write(f2.format(i[0] + i[1], i[2], t))
  outf.write(f3)

def filter_asrc(af_list, outf):
  
  f1 = r'''  <ItemGroup>
'''
  f2 = r'''  <YASM Include="..\..\{1:s}\{0:s}">
    <Filter>Source Files\mpn\yasm</Filter>
  </YASM>
'''
  f3 = r'''  </ItemGroup>
'''
  outf.write(f1)
  for i in af_list:
    outf.write(f2.format(i[0] + i[1], i[2], i[2]))
  outf.write(f3)


def gen_filter(name, hf_list, cf_list, af_list):
  
  f1 = r'''<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
'''
  f2 = r'''</Project>
'''
  fn = join(vc10_dir, name)
  makedirs(split(fn)[0], exist_ok=True)
  with open(fn, 'w') as outf:
    
    outf.write(f1)    
    filter_folders(cf_list, af_list, outf)
    filter_headers(hf_list, outf)
    filter_csrc(cf_list, outf)
    filter_asrc(af_list, outf)
    outf.write(f2)
    
# generate vcxproj file

def vcx_proj_cfg(plat, outf):
  
  f1 = r'''  <ItemGroup Label="ProjectConfigurations">
'''
  f2 = r'''    <ProjectConfiguration Include="{1:s}|{0:s}">
      <Configuration>{1:s}</Configuration>
      <Platform>{0:s}</Platform>
    </ProjectConfiguration>
'''
  f3 = r'''  </ItemGroup>
'''
  outf.write(f1)
  for conf in ('Release', 'Debug'):
    outf.write(f2.format(plat, conf))
  outf.write(f3)

def vcx_globals(name, outf):

  f1 = r'''  <PropertyGroup Label="Globals">
    <RootNamespace>{0:s}</RootNamespace>
    <Keyword>Win32Proj</Keyword>
  </PropertyGroup>
'''
  outf.write(f1.format(name))
  
def vcx_default_cpp_props(outf):
  
  f1 = r'''  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />
'''
  outf.write(f1)

def vcx_library_type(plat, is_dll, outf):
  
  f1 = r'''  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='{1:s}|{0:s}'" Label="Configuration">
    <ConfigurationType>{2:s}Library</ConfigurationType>
    <CharacterSet>MultiByte</CharacterSet>
  </PropertyGroup>
'''
  for conf in ('Release', 'Debug'):
    outf.write(f1.format(plat, conf, 'Dynamic' if is_dll else 'Static' ))

def vcx_cpp_props(outf):
  
  f1 = r'''  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
'''
  outf.write(f1)

def vcx_extensions(outf):

  f1 = r'''  <ImportGroup Label="ExtensionSettings">
    <Import Project="..\vsyasm.props" />
  </ImportGroup>
'''
  outf.write(f1)

def vcx_user_props(plat, outf):
  
  f1 = r'''  <ImportGroup Condition="'$(Configuration)|$(Platform)'=='{1:s}|{0:s}'" Label="PropertySheets">
    <Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" />
  </ImportGroup>
'''
  for conf in ('Release', 'Debug'):
    outf.write(f1.format(plat, conf))

def vcx_target_name_and_dirs(name, plat, is_dll, outf):
  
  f1 = r'''  <PropertyGroup>
    <_ProjectFileVersion>10.0.21006.1</_ProjectFileVersion>
'''
  f2 = r'''    <TargetName Condition="'$(Configuration)|$(Platform)'=='{1:s}|{0:s}'">{2:s}</TargetName>
    <IntDir Condition="'$(Configuration)|$(Platform)'=='{1:s}|{0:s}'">$(Platform)\$(Configuration)\</IntDir>
    <OutDir Condition="'$(Configuration)|$(Platform)'=='{1:s}|{0:s}'">$(SolutionDir)$(Platform)\$(Configuration)\</OutDir>
'''
  f3 = r'''  </PropertyGroup>
'''
  outf.write(f1)
  for conf in ('Release', 'Debug'):
    outf.write(f2.format(plat, conf, name))
  outf.write(f3)

def yasm_options(is_dll, outf):

  f1 = r'''    <YASM>
      <Defines>{0:s}</Defines>
      <IncludePaths>..\..\mpn\x86_64w\</IncludePaths>
      <Debug>true</Debug>
      <ObjectFileName>$(IntDir)mpn\</ObjectFileName>
      <ObjectFile>$(IntDir)mpn\</ObjectFile>
    </YASM>
'''

  outf.write(f1.format('DLL' if is_dll else ''))

def compiler_options(is_dll, is_debug, outf):
  
  f1 = r'''    <ClCompile>
      <Optimization>{0:s}</Optimization>
      <IntrinsicFunctions>true</IntrinsicFunctions>
      <AdditionalIncludeDirectories>..\..\</AdditionalIncludeDirectories>
      <PreprocessorDefinitions>{1:s}%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <RuntimeLibrary>MultiThreaded{2:s}</RuntimeLibrary>
      <ProgramDataBaseFileName>$(TargetDir)$(TargetName).pdb</ProgramDataBaseFileName>
      <DebugInformationFormat>ProgramDatabase</DebugInformationFormat>
    </ClCompile>
'''
  
  if is_dll:
    s1 = 'DEBUG;HAVE_CONFIG_H;__GMP_LIBGMP_DLL;__GMP_WITHIN_GMP;__GMP_WITHIN_GMPXX;'
    s2 = 'DLL'
  else:
    s1 = 'DEBUG;_LIB;HAVE_CONFIG_H;'
    s2 = ''
  if is_debug:
    opt, defines, crt = 'Disabled', '_' + s1, 'Debug' + s2
  else:
    opt, defines, crt = 'Full', 'N' + s1, s2
  outf.write(f1.format(opt, defines, crt))

def linker_options(outf):

  f1 = r'''    <Link>
      <GenerateDebugInformation>true</GenerateDebugInformation>
      <LargeAddressAware>true</LargeAddressAware>
    </Link>
'''
  outf.write(f1)

def vcx_post_build(outf):
  
  f1 = '''    <PostBuildEvent>
      <Command>cd ..\ 
postbuild "$(TargetPath)"</Command>
    </PostBuildEvent>
'''
  outf.write(f1)
  
def vcx_tool_options(plat, is_dll, outf):
  
  f1 = r'''  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='{1:s}|{0:s}'">
'''
  f2 = r'''  </ItemDefinitionGroup>
'''
  for is_debug in (False, True):
    outf.write(f1.format(plat, 'Debug' if is_debug else 'Release'))
    yasm_options(is_dll, outf)
    compiler_options(is_dll, is_debug, outf)
    if is_dll:
      linker_options(outf)
    vcx_post_build(outf)    
    outf.write(f2)
    
def vcx_hdr_items(hdr_list, outf):
  
  f1 = r'''  <ItemGroup>
'''
  f2 = r'''    <ClInclude Include="..\..\{0:s}" />
'''
  f3 = r'''  </ItemGroup>
'''
  outf.write(f1)
  for i in hdr_list:
    outf.write(f2.format(i))    
  outf.write(f3)
   
def vcx_c_items(cf_list, plat, outf):
  
  f1 = r'''  <ItemGroup>
'''
  f2 = r'''    <ClCompile Include="..\..\{0[0]:s}{0[1]:s}" />
'''
  f3 = r'''    <ClCompile Include="..\..\{0[2]:s}\{0[0]:s}{0[1]:s}">
      <ObjectFileName Condition="'$(Configuration)|$(Platform)'=='Debug|{1:s}'">$(IntDir){2:s}\</ObjectFileName>
      <ObjectFileName Condition="'$(Configuration)|$(Platform)'=='Release|{1:s}'">$(IntDir){2:s}\</ObjectFileName>
    </ClCompile>
'''
  f4 = r'''  </ItemGroup>
'''
  outf.write(f1)
  for nxd in cf_list:
    if nxd[2] == '':
      outf.write(f2.format(nxd))
    else:
      outf.write(f3.format(nxd, plat, 'mpn' if nxd[2].endswith('generic') else nxd[2]))
  outf.write(f4)

def vcx_a_items(af_list, outf):
  
  f1 = r'''  <ItemGroup>
'''
  f2 = r'''    <YASM Include="..\..\{0[2]:s}\{0[0]:s}{0[1]:s}" />
'''
  f3 = r'''  </ItemGroup>
'''
  outf.write(f1)
  for nxd in af_list:
    outf.write(f2.format(nxd))
  outf.write(f3)

def gen_vcxproj(proj_name, file_name, plat, is_dll, hf_list, cf_list, af_list):
  
  f1 = r'''<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
'''
  f2 = r'''  <PropertyGroup Label="UserMacros" />
'''
  f3 = r'''  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
'''
  f4 = r'''  <ImportGroup Label="ExtensionTargets">
    <Import Project="..\vsyasm.targets" />
  </ImportGroup>
'''
  f5 = '''</Project>
'''
  
  with open(join(vc10_dir, file_name), 'w') as outf:
    outf.write(f1)
    vcx_proj_cfg(plat, outf)
    vcx_globals(proj_name, outf)
    vcx_default_cpp_props(outf)
    vcx_library_type(plat, is_dll, outf)
    vcx_cpp_props(outf)
    vcx_extensions(outf)    
    vcx_user_props(plat, outf)
    outf.write(f2)
    vcx_target_name_and_dirs(proj_name, plat, is_dll, outf)
    vcx_tool_options(plat, is_dll, outf)
    vcx_hdr_items(hf_list, outf)
    vcx_c_items(cf_list, plat, outf)
    vcx_a_items(af_list, outf)
    outf.write(f3)
    outf.write(f4)
    outf.write(f5)

t = find_src(c_directories)
c_hdr_list = t[0]
c_src_list = t[1]
if t[2] or t[3]:
  print('found C++ and/or assembler file(s) in a C directory')
for f in c_hdr_list:
  print(f)
print()
for f in c_src_list:
  print(f)
print()

t = find_src(['cxx'])
cc_hdr_list = t[0]
cc_src_list = t[2]
if t[1] or t[3]:
  print('found C+ and/or assembler file(s) in a C++ directory')
for f in cc_hdr_list:
  print(f)
print()
for f in cc_src_list:
  print(f)
print()

t = find_src([r'mpn\generic'])
gc_hdr_list = t[0]
gc_src_list = t[1]
if t[1] or t[3]:
  print('found C++ and/or assembler file(s) in a C directory')
for f in gc_hdr_list:
  print(f)
print()
for f in gc_src_list:
  print(f)
print()

mpn_32 = find_asm(mpir_dir + 'mpn/x86w', gc_src_list)
mpn_32['gc-win32'] = [ gc_hdr_list, gc_src_list, [], [] ]
del mpn_32['']
mpn_64 = find_asm(mpir_dir + 'mpn/x86_64w', gc_src_list)
mpn_64['gc-x64'] = [ gc_hdr_list, gc_src_list, [], [] ]
del mpn_64['']

err = False
config = ''
mode = ''
while True:
  cnt = 0
  for v in sorted(mpn_32):
    cnt += 1
    print('{0:2d}. {1:12s} (win32)'.format(cnt, v))
  for v in sorted(mpn_64):
    cnt += 1
    print('{0:2d}. {1:12s}   (x64)'.format(cnt, v))
  if err:
    s = input('please enter a number <= {0:d} (0 to exit)? '.format(cnt))
    err = False
  else:
    s = input('Number of configuation to build (0 to exit)? ')
  try:
    n = int(s)
    if n < 1:
      n = 0
      break
    if n <= len(mpn_32):
      config = sorted(mpn_32)[n - 1]
      mode = 'win32'
      mpn_f = mpn_32[config]
      break
    elif n <= len(mpn_32) + len(mpn_64):
      config = sorted(mpn_64)[n - len(mpn_32) - 1]
      mode = 'x64'
      mpn_f = mpn_64[config]
      break
  except:
    pass
  err = True
if n == 0:
  exit()
  
if mode == 'x64':
  for l in mpn_f[1:]:
    for t in l:
      if t[0].startswith('preinv_'):
        if (mode == 'x64' and t[0] == 'preinv_divrem_1' or
            mode == 'win32' and t[0] == 'preinv_mod_1'):
          l.remove(t)
  
print(config, mode)

# generate mpir.h and gmp.h from gmp_h.in
gmp_h_32 = '''
#define __GMP_BITS_PER_MP_LIMB              32
#define GMP_LIMB_BITS                       32
#if defined _LONG_LONG_LIMB
#  undef _LONG_LONG_LIMB 1 
#endif
#if defined _WIN64
#  undef _WIN64 
#endif
#define GMP_NAIL_BITS                       0 
#define SIZEOF_MP_LIMB_T (GMP_LIMB_BITS >> 3) 
'''
gmp_h_64 = '''
#define __GMP_BITS_PER_MP_LIMB              64
#define GMP_LIMB_BITS                       64
#if !defined _LONG_LONG_LIMB
#  define _LONG_LONG_LIMB 1 
#endif
#if !defined _WIN64
#define _WIN64 
#endif
#define GMP_NAIL_BITS                       0 
#define SIZEOF_MP_LIMB_T (GMP_LIMB_BITS >> 3) 
'''

try:
  lines = open(join(mpir_dir, 'gmp-h.in'), 'r').readlines()
except IOError:
  print('error attempting to read from gmp_h.in')
  exit()
try:
  tfile = join(mpir_dir, 'tmp.h')
  with open(tfile, 'w') as outf:
    first = True
    for line in lines:
      if search('@\w+@', line):
        if first:
          first = False
          outf.writelines(gmp_h_32 if mode == 'win32' else gmp_h_64)  
      else:
        outf.writelines([line])
        
  # write result to mpir.h but only overwrite the existing 
  # version if this version is different (don't trigger an
  # unnecessary rebuild)
  write_f(tfile, join(mpir_dir, 'mpir.h'))
  write_f(tfile, join(mpir_dir, 'gmp.h'))
  unlink(tfile)
except IOError:    
  print('error attempting to create mpir.h from gmp-h.in')
  exit()

# generate config.h

try:
  tfile = join(mpir_dir, 'tmp.h')
  with open(tfile, 'w') as outf:
    for i in mpn_f[3]:
      outf.writelines(['#define HAVE_NATIVE_{0:s} 1\n'.format(i[0])])
      
  append_f(join(vc10_dir, 'cfg.h'), tfile)
  write_f(tfile, join(mpir_dir, 'config.h'))
  unlink(tfile)
except IOError:
  print('error attempting to write to {0:s}'.format(tfile))
  exit()
  
# generate longlong.h and copy gmp-mparam.h

try:
  li_file = None
  for i in mpn_f[0]:
    if i[0] == 'longlong_inc':
      li_file = join(mpir_dir, join(i[2], r'longlong_inc.h'))
    if i[0] == 'gmp-mparam':
      write_f(join(mpir_dir, join(i[2], 'gmp-mparam.h')), join(mpir_dir, 'gmp-mparam.h'))
  
  if not li_file or not exists(li_file):
    print('error attempting to read {0:s}'.format(li_file))
    exit()
    
  tfile = join(mpir_dir, 'tmp.h')    
  write_f(join(mpir_dir, 'longlong_pre.h'), tfile)
  append_f(li_file, tfile)
  append_f(join(mpir_dir, 'longlong_post.h'), tfile)
  write_f(tfile, join(mpir_dir, 'longlong.h'))
  unlink(tfile)
except IOError:
  print('error attempting to generate longlong.h')
  exit()
  
# generate vcxproj filter

hf_list = ('config.h', 'gmp-impl.h', 'longlong.h', 'mpir.h', 'gmp-mparam.h')
af_list = sorted(mpn_f[2] + mpn_f[3]) 

# set up DLL build
is_DLL = True
proj_name = 'mpir'
vcx_name = 'dll_mpir_' + config + '\\dll_mpir_' + config + '.2.vcxproj'
gen_filter(vcx_name + '.filters', hf_list, c_src_list + cc_src_list + mpn_f[1], af_list)
gen_vcxproj(proj_name, vcx_name, mode, is_DLL, hf_list, c_src_list + cc_src_list + mpn_f[1], af_list)

# set up LIB build
is_DLL = False
proj_name = 'mpir'
vcx_name = 'lib_mpir_' + config + '\\lib_mpir_' + config + '.2.vcxproj'
gen_filter(vcx_name + '.filters', hf_list, c_src_list + mpn_f[1], af_list)
gen_vcxproj(proj_name, vcx_name, mode, is_DLL, hf_list, c_src_list + mpn_f[1], af_list)
  
exit()

for x in sorted(mpn_f[0] + mpn_f[1]):
  print(x)
print()
for x in sorted(mpn_f[2] + mpn_f[3]):
  print(x)
print()
exit()

# mpn_files = dict()
# mpn_files.update(mpn_32)
# mpn_files.update(mpn_64)
for x in mpn_f[config]:
  print(x)
  if False:  
    print('1:')
    for y in mpn_files[x][0]:
      print(y)
    print('2:')
    for y in mpn_files[x][1]:
      print(y)
    print('3:')
    for y in mpn_files[x][2]:
      print(y)
    print('4:')
    for y in mpn_files[x][3]:
      print(y)
    print()
  for y in sorted(x[2] + x[3]):
    print(y)
  print()
  print()
  
exit()


mpn_dirs =  ('mpn/generic', 'mpn/x86_64w', 'mpn/x86w' )

# compile a list of files in directories in 'dl' under root 'r' with extension 'p'
def findf(r, dl, p):
  l = []
  for d in dl:
    for root, dirs, files in os.walk(r + d):
      relp = os.path.relpath(root, r)  # path relative to mpir root directory
      if '.svn' in dirs:
        dirs.remove('.svn')            # ignore SVN directories
      if d == '' or root.endswith('build.vc10'):
        for d in reversed(dirs):       # don't scan build.vc10 subdirectories
          dirs.remove(d)
      for f in files:
        if f.endswith(p):
          l += [(tuple(relp.split('\\')), f)]
  return sorted(l)
  
hdr_list = findf(dpath, c_dirs, '.h')
for x in hdr_list:
  print(x)
print()

src_list = findf(dpath, c_dirs, '.c')
for x in src_list:
  print(x)
print()

cpp_list = findf(dpath, ['cpp'], '.cc')
for x in cpp_list:
  print(x)
print()

gnc_list = findf(dpath + 'mpn/', ['generic'], '.c')
for x in gnc_list:
  print(x)
print()

w32_list = findf(dpath + 'mpn/', ['x86w'], '.asm')
for x in w32_list:
  print(x)
print()

x64_list = findf(dpath + 'mpn/', ['x86_64w'], '.asm')
for x in x64_list:
  print(x)
print()

nd = dict([])
for d, f in gnc_list:
  n, x = os.path.splitext(f)
  nd[n] = nd.get(n, []) + [(d, 'c')]
for d, f in x64_list:
  n, x = os.path.splitext(f)
  nd[n] = nd.get(n, []) + [(d, 'asm')]
for d, f in w32_list:
  n, x = os.path.splitext(f)
  nd[n] = nd.get(n, []) + [(d, 'asm')]
for x in nd:
  print(x, nd[x])