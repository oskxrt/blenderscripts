#!BPY

"""
Name: 'FEI 2010 Files (*.FEF)'
Blender: 242
Group: 'Import'
Tooltip: 'KONAMI FEF Files'
"""

__author__ = "Skunk"
__url__ = ("", "")
__version__ = "1.0"
__bpydoc__ = ""

# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****


import Blender
from Blender import *
from Blender import sys as bsys
from Blender.Window import FileSelector

REG_KEY = 'fef_reg'
EXPORT_DIR = ''
IMPORT_DIR = ''

tooltips = {
	'EXPORT_DIR': "default / last folder used to export .sef files to",
	'IMPORT_DIR': "default / last folder used to import .sef files from"
}

def update_RegistryInfo():
	d = {}
	d['EXPORT_DIR'] = EXPORT_DIR
	d['IMPORT_DIR'] = IMPORT_DIR
	Blender.Registry.SetKey(REG_KEY, d, True)

# Looking for a saved key in Blender.Registry dict:
rd = Blender.Registry.GetKey(REG_KEY, True)

if rd:
	try:
		EXPORT_DIR = rd['EXPORT_DIR']
		IMPORT_DIR = rd['IMPORT_DIR']
	except KeyError: update_RegistryInfo()

else:
	update_RegistryInfo()


class grp:
	def __init__(self):
		self.name      = ''
		self.obj_count = 0
		self.obj_list  = []

class Obj:
	def __init__(self):
		self.name   = ''
		self.mat    = ''
		self.vlist  = []
		self.uvlist = []
		self.vcol   = []
		self.flist  = []

class mat:
	def __init__(self):
		self.name = ''
		self.tex  = ''

class lit:
	def __init__(self):
		self.energy	= 0
		self.x		= 0
		self.y		= 0
		self.z		= 0

class rebounds:
	def __init__(self):
		self.name  = ''
		self.parts = 0
		self.vlist = []


groups = []
mats = []
lights = []
rebound = []

global import_dir,weather
found = 0

def load_data(file):
#	global import_dir,weather
	global import_dir, tipo
	
	for line in file:
		if line.find('Type') >=0:
			tipo = line.split('=')[1].replace('"','').replace(' ','')
			found = 1 
			break
#	if not found:
#		weather = 'DF'

	file.next()
	for line in file:
		if line.find('Materials') >=0:
			materials = int(line.split('=')[1])
			found = 1 
			break
	

	file.next()
	for mt in range(materials):
		line = file.next()
		m = mat()		
		m.name = "%s"% line.split()[0]
		if len(line.split()) == 2:
			m.tex  = line.split()[1]
		elif len(line.split()) > 2:
			m.tex = line.split()[1]
			for n in xrange(len(line.split())-2):
				m.tex += " " + line.split()[n+2]
		else:
			Blender.Draw.PupMenu('Error: Loading textures.')
			return -1
		m.tex = m.tex.replace('"','')
		if not bsys.exists(m.tex):
			Blender.Draw.PupMenu('Error:'+ m.tex + ' not found.')
			return -1
		mats.append(m)

	for line in file:
		if line.find('Meshes') >=0:
			meshes = int(line.split('=')[1])
			found = 1 
			break
	if not found:
		Blender.Draw.PupMenu('Meshes not found in file')
		return -1

	file.next()
	for objs in range(meshes):
		line = file.next()
		line = line.split('=')[1]
		g = grp()
		g.name = line.split()[0].replace('"','')
		g.obj_count = int(line.split()[1])
		for gr in range(g.obj_count):
			new = Obj()
			new.vlist  = []
			new.uvlist = []
			new.vcol   = []
			new.flist  = []
			vertex  = 0
			faces   = 0
			line = file.next()
			new.name  = g.name + '-' + line.split()[0]
			new.mat   = line.split()[1]
			line = file.next()
			vertex  = int(line)
			for ver in range(vertex):
				line = file.next()
				try:
					x,y,z,u,v = float(line.split()[0]),float(line.split()[1]),float(line.split()[2]),float(line.split()[3]),1-float(line.split()[4])
					new.vlist.append((x,y,z))
					new.uvlist.append((u,v))
					new.vcol.append(line.split()[5])
				except:
					Blender.Draw.PupMenu('Error importing Vertex list.')
					return -1
			
			line = file.next()
			faces  = int(line)
			for fac in range(faces):
				try:
					line = file.next()
					if len(map(int,line.split())) >3:
						a,b,c,d = map(int,line.split())
						new.flist.append((a,b,c,d))
					else:
						a,b,c = map(int,line.split())
						new.flist.append((a,b,c))
				except:
					Blender.Draw.PupMenu('Error importing Faces.')
					return -1
	
			g.obj_list.append(new)
		groups.append(g)
	mats.sort()
	found = -1
        return 1
	
def import2blender():
	global import_dir,tipo
	scene_name = 'FEI-%s'%tipo
	sc = Scene.New(scene_name)
	sc.makeCurrent()
	#sc = Scene.GetCurrent()
	screen_list = Window.GetScreens()
	for screens in screen_list:
		Window.SetScreen(screens)
		sc.makeCurrent()
	Window.SetScreen(screen_list[2])
	# Load Materials
	mat = []
	for m in mats:
		material = Material.New(m.name)
		material.rgbCol = [1.0,1.0,1.0]
		texture = Texture.New(m.name)
		texture.setType('Image')
		texture.useAlpha
		#print m.tex
		if bsys.exists(m.tex):
			img = Image.Load(m.tex)
			texture.image = img
			texture.imageFlags |= Blender.Texture.ImageFlags.USEALPHA
			material.setTexture(0, texture, Texture.TexCo.UV,Texture.MapTo.ALPHA|Texture.MapTo.COL)
		else:
			Blender.Draw.PupMenu('Could not load %s texture'% (m.tex))
	 	mat.append(material)	

	#Load mesh structures to Blender
	for g in groups:
		ob_list = []
		for o in g.obj_list:
			mesh = Blender.NMesh.New()
			mesh.name = o.name
			mesh.hasFaceUV(1)
			mesh.hasVertexColours(1)
			#Assign Material to Mesh and load Texture for UVs
			tex = ''
			for m in mat:
				if o.mat == m.name:
					mesh.materials.append(m)
					textu = m.getTextures()
					if bsys.exists(textu[0].tex.image.filename):
						tex = textu[0].tex.image
					break
			if not mesh.materials:
				try:
					newmat = Material.Get(o.mat)
				except:
					newmat = Material.New(o.mat)
				mesh.materials.append(newmat)

			#Import Vertices
			for ver in o.vlist:
				bvert = Blender.NMesh.Vert(ver[0],ver[1],ver[2])
				mesh.verts.append(bvert)

			#Import faces with UV and Vertex Colours
			for fac in o.flist:
				bface = Blender.NMesh.Face()
				bface.mode |= Blender.NMesh.FaceModes['TWOSIDE'] 
				if tex:
					bface.mode |= Blender.NMesh.FaceModes['TEX']
					bface.transp = Blender.NMesh.FaceTranspModes['ALPHA']
					bface.image = tex
				for fa in range(len(fac)):
					bface.v.append(mesh.verts[fac[fa]])
					bface.uv.append(o.uvlist[fac[fa]])
					col = Blender.NMesh.Col()
					col.r = int((o.vcol[fac[fa]][4]+o.vcol[fac[fa]][5]),16)
					col.g = int((o.vcol[fac[fa]][6]+o.vcol[fac[fa]][7]),16)
					col.b = int((o.vcol[fac[fa]][8]+o.vcol[fac[fa]][9]),16)
					col.a = int((o.vcol[fac[fa]][2]+o.vcol[fac[fa]][3]),16)
					bface.col.append(col)
				mesh.faces.append(bface)	
			mesh.mode = 0
			object = Blender.NMesh.PutRaw(mesh)
			object.setName(o.name)
			ob_list.append(object)
		# Create a group for this import.
		grp = Object.New("Empty",g.name)
		sc.link(grp)
		grp.makeParent(ob_list)
	return 1
	
# File Selector callback:
def fs_callback(filename):
	global IMPORT_DIR, EXPORT_DIR, import_dir, tipo
	tipo = ''
	
	if not filename.endswith('.fef'): filename = '%s.fef' % filename


	Blender.Window.WaitCursor(1)
	starttime = bsys.time()

	import_dir = bsys.dirname(filename)
	if import_dir != IMPORT_DIR:
		IMPORT_DIR = import_dir
		update_RegistryInfo()


	file = open(filename,"r")
	header = file.readline()
	if header != '//Face and Hair Exchange File (c)2010 by Skunk\n':
		print "Wrong file!"
		Blender.Draw.PupMenu('Wrong File!')
		file.close()
		return

	if not load_data(file):
		Blender.Draw.PupMenu('Error in input file!')
		file.close()
		return

	if not import2blender():
		Blender.Draw.PupMenu('Error in input file!')
		file.close()
		return		
	
	file.close()

	endtime = bsys.time() - starttime
	print "Data imported in %.3f seconds." % endtime

	Blender.Window.WaitCursor(0)
	return


objs = Blender.Object.Get()

if objs:
	Blender.Draw.PupMenu('WARNING: There are objects yet in the scene.')
fname = "*.fef"
if IMPORT_DIR:
	fname = bsys.join(IMPORT_DIR, bsys.basename(fname))
FileSelector(fs_callback, "Import FEF", fname)
