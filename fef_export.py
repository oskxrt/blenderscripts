#!BPY

"""
Name: 'FEI 2010 Files (*.FEF)'
Blender: 242
Group: 'Export'
Tooltip: 'KONAMI FEF Files'
"""
__author__ = "Skunk"
__url__ = ("", "")
__version__ = "1.1"
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



import Blender, meshtools, BPyMesh
from Blender import *
from Blender import sys as bsys
from Blender.Window import FileSelector

REG_KEY = 'fef_reg'
EXPORT_DIR = ''
IMPORT_DIR = ''
idxcero = 0
tooltips = {
	'EXPORT_DIR': "default / last folder used to export .fef files to",
	'IMPORT_DIR': "default / last folder used to import .fef files from"
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


class mat:
	def __init__(self):
		self.oriname = ''
		self.newname = ''
		self.texture = ''

class grp:
	def __init__(self):
		self.name      = ''
		self.obj_count = 0
		self.obj_list  = []

class Obj:
	def __init__(self):
		self.name   = ''
		self.tex    = ''
		self.vlist  = []
		self.uvlist = []
		self.vcol   = []
		self.flist  = []

#Code Taken from 3ds Exporter
def uv_key(uv):
	return round(uv.x, 6), round(uv.y, 6)

class tri_wrapper(object):
	'''Class representing a triangle.
	Used when converting faces to triangles'''
	
	__slots__ = 'vertex_index', 'faceuvs', 'vcol', 'offset'
	def __init__(self, vindex=(0,0,0), faceuvs=None, vcol=None):
		self.vertex_index= vindex
		self.faceuvs= faceuvs
		self.vcol = vcol
		self.offset= [0, 0, 0] # offset indicies


def split_into_tri(face, do_uv=False, do_col=False):
	'''Split a quad face into two triangles'''
	v = face.v
	first_tri = tri_wrapper((v[0].index, v[1].index, v[2].index))
	second_tri = tri_wrapper((v[0].index, v[2].index, v[3].index))
	
	if (do_uv):
		uv = face.uv
		first_tri.faceuvs= uv_key(uv[0]), uv_key(uv[1]), uv_key(uv[2])
		second_tri.faceuvs= uv_key(uv[0]), uv_key(uv[2]), uv_key(uv[3])
	if (do_col):
		first_tri.vcol  = face.col[0],face.col[1],face.col[2]
		second_tri.vcol = face.col[0],face.col[2],face.col[3]

	return [first_tri, second_tri]
	
	
def extract_triangles(mesh):
	'''Extract triangles from a mesh.
	
	If the mesh contains quads, they will be split into triangles.'''
	tri_list = []
	do_uv  = mesh.faceUV
	for face in mesh.faces:
			try:
				do_col = face.col
			except:
				do_col = 0
			num_fv = len(face)
			if num_fv==3:
				new_tri = tri_wrapper((face.v[0].index, face.v[1].index, face.v[2].index))
				if (do_uv):
					new_tri.faceuvs= uv_key(face.uv[0]), uv_key(face.uv[1]), uv_key(face.uv[2])
				if (do_col):
					new_tri.vcol = face.col[0],face.col[1],face.col[2]
				tri_list.append(new_tri)
				
			else: #it's a quad
				tri_list.extend( split_into_tri(face, do_uv, do_col) )
		
	return tri_list

def remove_face_uv(verts, tri_list, matrix):
	'''Remove face UV coordinates from a list of triangles.
		
	Since 3ds files only support one pair of uv coordinates for each vertex, face uv coordinates
	need to be converted to vertex uv coordinates. That means that vertices need to be duplicated when
	there are multiple uv coordinates per vertex.'''
	
	# initialize a list of UniqueLists, one per vertex:
	#uv_list = [UniqueList() for i in xrange(len(verts))]
	unique_uvs= [{} for i in xrange(len(verts))]
	
	# for each face uv coordinate, add it to the UniqueList of the vertex
	for tri in tri_list:
		for i in xrange(3):
			# store the index into the UniqueList for future reference:
			# offset.append(uv_list[tri.vertex_index[i]].add(_3ds_point_uv(tri.faceuvs[i])))
			context_uv_vert= unique_uvs[tri.vertex_index[i]]
			uvkey= tri.faceuvs[i]
			try:
				offset_index, uv_3ds= context_uv_vert[uvkey]
			except:
				offset_index= len(context_uv_vert)
				context_uv_vert[tri.faceuvs[i]]= offset_index, uvkey
			tri.offset[i]= offset_index

		
	# At this point, each vertex has a UniqueList containing every uv coordinate that is associated with it
	# only once.
	
	# Now we need to duplicate every vertex as many times as it has uv coordinates and make sure the
	# faces refer to the new face indices:
	vert_index = 0
	vert_array = []
	uv_array = []
	index_list=[]
	for i,vert in enumerate(verts):
		index_list.append(vert_index)
		x, y, z = meshtools.apply_transform(vert.co,matrix)
		uvmap = [None] * len(unique_uvs[i])
		for ii, uv_3ds in unique_uvs[i].itervalues():
			# add a vertex duplicate to the vertex_array for every uv associated with this vertex:
			vert_array.append((x,y,z))
			# add the uv coordinate to the uv array:
			# This for loop does not give uv's ordered by ii, so we create a new map
			# and add the uv's later
			# uv_array.add(uv_3ds)
			uvmap[ii] = uv_3ds

		# Add the uv's in the correct order
		for uv_3ds in uvmap:
			# add the uv coordinate to the uv array:
			uv_array.append(uv_3ds)

		vert_index += len(unique_uvs[i])
	
	# Make sure the triangle vertex indices now refer to the new vertex list:
	for tri in tri_list:
		for i in xrange(3):
			tri.offset[i]+=index_list[tri.vertex_index[i]]
		tri.vertex_index= tri.offset
	
	return vert_array, uv_array, tri_list


def load_meshes(me,new,matrix):

	tri_list = extract_triangles(me)

	if me.faceUV:
		new.vlist, new.uvlist, tri_list = remove_face_uv(me.verts,tri_list,matrix)
	else:
		for vert in me.verts:
			x, y, z = meshtools.apply_transform(vert.co,matrix)
			new.vlist.append((x,y,z))
			new.uvlist.append((0.0,0.0))

	vcolors = {}
	for tri in tri_list:
		for j in xrange(3):
			index = tri.vertex_index[j]
			if not tri.vcol:
				color = Blender.NMesh.Col()
				color.a = 255
				color.r = 255
				color.g = 255
				color.b = 255
			else:
				color = tri.vcol[j]
			vcolors.setdefault(index,[color.a, color.r,color.g,color.b])

	for v in xrange(len(new.vlist)):
		new.vcol.append(vcolors[v])

	for tri in tri_list:
		new.flist.append((tri.vertex_index))
	
	return 1


def save_file(file,g):
	if g.obj_count > 0:
		file.write("Name = \"%s\" %d\n" % (g.name,g.obj_count))
		g.obj_list.sort(key=lambda obj:obj.name)
		for o in g.obj_list:
			file.write("%s %s\n%d\n" % (o.name,o.tex,len(o.vlist)))
			for i in range(len(o.vlist)):
				file.write("%8f %8f %8f " % tuple(o.vlist[i]))
				u,v = o.uvlist[i][0], o.uvlist[i][1]
				file.write("%8f %8f 0x" % (u,1-v))
				for j in range(len(o.vcol[i])):
					file.write("%02X" % o.vcol[i][j])
				file.write("\n")
			file.write("%d\n" % len(o.flist))
			for f in range(len(o.flist)):
				file.write("%d %d %d \n"	% tuple(o.flist[f]))
	
def add_mat(material,o):
	found = False
	try:
		textu = material.getTextures()
	except:
		print "Has Material but Empty: %s"%o.getName()
		return 'FFFF'
	if textu[0] != None:
		if textu[0].tex.type == Texture.Types.IMAGE:
			new_mat = mat()
			new_mat.oriname = material.name
			new_mat.newname = ''
			try:
				new_mat.texture = textu[0].tex.image.filename
				for m in range(len(mat_list)):
					if mat_list[m].texture == new_mat.texture:
						found = True
						break
			except:
				print "No Texture Loaded: %s\n"%o.getName()
				return material.name
			if not found:
				mat_list.append(new_mat)
			return new_mat.texture
	print "No Texture 1st Pos: %s\n"%o.getName()
	return material.name

def load_objs(parent,group):
	group.obj_count = 0
	for o in objs:
		if o.getParent() == parent:
			new = Obj()
			try:
				new.name = o.getName().split('-')[1] + '-' + o.getName().split('-')[2]
			except:
				Blender.Draw.PupMenu("ERROR:%t| Object name \""+o.getName()+"\"not valid.|%l|Name should look like OBJECT_NAME-XX-XX")
				return -1
			me = BPyMesh.getMeshFromObject(o, None, True, False, tp)
			#me = NMesh.GetRaw(o.data.name)
			if len(me.materials) >0:
				new.tex = add_mat(me.materials[0],o)
			else:
				print "No Material: %s\n"%o.getName()
				new.tex = 'FFFF'
			if load_meshes(me,new,o.matrix) == -1:
				Blender.Draw.PupMenu('ERROR:%t| Unexpected Error. ')
				return -1
			group.obj_list.append(new)
			group.obj_count += 1
			
	return 1
                
# File Selector callback:
def fs_callback(filename):
	global EXPORT_DIR

	if not filename.endswith('.fef'): filename = '%s.fef' % filename

	if bsys.exists(filename):
		if Blender.Draw.PupMenu('OVERWRITE?%t|File exists') != 1:
			return

	editmode = Blender.Window.EditMode()    # are we in edit mode?  If so ...
	if editmode: Blender.Window.EditMode(0) # leave edit mode before getting the mesh

	starttime = bsys.time()

	export_dir = bsys.dirname(filename)
	if export_dir != EXPORT_DIR:
		EXPORT_DIR = export_dir
		update_RegistryInfo()

        objs_count=0
        for o in objs:
                objs_count+=1
                #Order parts to assing textures starting from LEFT_EYE
                grp_mat = ["F00","F01","F02","F03","F04","F05","F06"]
                                                          
                #Ordered Parts to meet order in faces
                grp_names = ["F00","F01","F02","F03","F04","F05","F06"]
                name =  "F00 %x0|F01 %x1|F02 %x2|F03 %x3|F04 %x4|F05 %x5|F06 %x6"
                new_names = ["F00","F01","F02","F03","F04","F05","F06"]

	#asign array names                          
        tmp_name = ''
	#check for correct names
	for o in objs:
		if o.getType() == "Empty":
			if o.getName() not in (grp_names):
				tmp_name = "Part Name %s is wrong, Please Select the one that matches. " % o.getName()
				tmp_name += "%t|"
				tmp_name += name
				result = Blender.Draw.PupMenu(tmp_name, 10)
				if  result != -1:
					o.setName(new_names[result])
				else:
					return
	del new_names
	del name
	del tmp_name

	Blender.Window.WaitCursor(1)
	for o in objs:
			g = grp()
			g.name = o.getName()
			if load_objs(o,g) == -1:
				return
			groups.append(g)
	
	if len(mat_list) > 51:
		Blender.Draw.PupMenu('ERROR:%t| Cant use more than 51 Textures,|%l|Please, fix it before export. ')
		return 

	groups_ordered_mat = []
	for order in range(len(grp_mat)):
		for gr in groups:
			if gr.name == grp_mat[order]:
				groups_ordered_mat.append(gr)
				break
                
        tipo = tp.getName()
        tipo = tipo.split('-')[1]
        if tipo[0]  == "F":                
                tex_id = 0x2752
        else:
                tex_id = 0x2753
                
	for gr in groups_ordered_mat:
		gr.obj_list.sort(key=lambda obj:obj.name)
		for o in gr.obj_list:
			for m in mat_list:
				if o.tex == m.texture:
					if m.newname == '':
						m.newname = "%04x" % tex_id
                                                tex_id += 1
        				o.tex = m.newname
                                        break

	mat_list.sort(key=lambda obj:obj.newname)

	groups_ordered = []
	for order in range(len(grp_names)):
		for gr in groups_ordered_mat:
			if gr.name == grp_names[order]:
				groups_ordered.append(gr)
				break

	del groups_ordered_mat

		
	file = open(filename,"w")
	file.write("//Face and Hair Exchange File (c)2010 by Skunk\n\n")

	tipo = tp.getName()
        tipo = tipo.split('-')[1]

                        
	file.write("Type = \"%s\"\n\n"%tipo.replace("\n",""))
	
	file.write("Materials = %d\n\n"% len(mat_list))
	for m in mat_list:
		file.write("%s \"%s\"\n"%(m.newname,m.texture))

	o_count=0
	for gr_o in groups_ordered:
		if gr_o.obj_count > 0:
			o_count += 1
	file.write("\nMeshes = %d\n\n"% o_count)
	for gr_o in groups_ordered:
		save_file(file,gr_o)
	
	file.close()

	endtime = bsys.time() - starttime
	print "Data exported in %.3f seconds." % endtime

	Blender.Window.WaitCursor(0)
	return


groups = []
mat_list = []
tp = Scene.GetCurrent()
objs = tp.getChildren()

if not objs:
	Blender.Draw.PupMenu('ERROR: no objects in scene')
else:
	fname = "*.fef"
	if EXPORT_DIR:
		fname = bsys.join(EXPORT_DIR, bsys.basename(fname))
	FileSelector(fs_callback, "Export FEF", fname)
