import igraph as ig
import networkx as nx
import osmnx as ox
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors

from pathlib import Path

import sys
ox.config(use_cache=True, log_console=True)

class Centrality:
	def __init__(self, 
				city='Munich, Germany',
				city_boundaries = [48.22,11.75,48.04,11.38]):
		self.city = city
		# boundaries in NEWS format
		self.city_boundaries = city_boundaries
	
	def load_network(self, centrality_type):
		self.G = ox.load_graphml(self.city+"_"+centrality_type)
		self.G_nx = nx.relabel.convert_node_labels_to_integers(self.G)

	def create_network(self, 
						create_by = 'name', 
						network_type='drive'):
		self.network_type = network_type
		if create_by == 'name':
			self.G = ox.graph_from_place(self.city, network_type=self.network_type)
		if create_by == 'bbox':
			# create network from that bounding box
			self.G = ox.graph_from_bbox(self.city_boundaries[0], 
									self.city_boundaries[3], 
									self.city_boundaries[1], 
									self.city_boundaries[2], network_type='drive')
		if create_by == 'address':
			self.G = ox.graph_from_address(self.city, network_type='drive')

		self.G_nx = nx.relabel.convert_node_labels_to_integers(self.G)
	
	def calculate_node_centrality(self, centrality_type = 'closeness', centrality_cutoff=None,
								weight='length', mode='ALL'):
		# Calculate node centrality
		self.weight = weight
		self.mode = mode
		self.centrality_type = centrality_type
		self.centrality_cutoff = centrality_cutoff

		self.G_ig = ig.Graph(directed=True)
		self.G_ig.add_vertices(list(self.G_nx.nodes()))
		self.G_ig.add_edges(list(self.G_nx.edges()))

		# print(nx.to_dict_of_dicts(self.G_nx))
		# self.G_ig.vs['osmid'] = list(nx.get_node_attributes(self.G_nx, 'osmid').values())
		temp = list(nx.get_edge_attributes(self.G_nx, weight).values())
		l_weights = [num if num>0 else 1 for num in temp]

		self.G_ig.es[weight] = l_weights

		# closeness is for a node, not for a edge
		if self.centrality_type == 'closeness':
			cc = self.G_ig.closeness(vertices=None, mode='ALL', cutoff=self.centrality_cutoff,
									 weights=self.weight, normalized=True)
		# If the graph is not connected, and there is no path between two vertices, the number of vertices is used 
		# instead the length of the geodesic. This is always longer than the longest possible geodesic.
		# My comment: This may be not true for weighted graphs, so the ipgraph's centrality is an approximation
		
		elif self.centrality_type == 'betweenness':
			cc = self.G_ig.betweenness(vertices=None, directed=True, cutoff=None, weights=self.weight, nobigint=True)

		else:
			raise('Method not defined for this centrality')

		cc_dict = dict(zip(self.G.nodes, [np.float(i) for i in cc]))
		nx.set_node_attributes(self.G, cc_dict, self.centrality_type+"_"+str(self.centrality_cutoff))

	def calculate_edge_centrality(self, centrality_type = 'closeness'):
		self.attribute = centrality_type
		self.centrality_type = centrality_type
		if self.centrality_type == 'closeness':
			nodes = list(self.G.nodes)
			data_nodes = list(self.G.nodes(data=True))
			for edge in self.G.edges(data=True):
				node_from = data_nodes[nodes.index(edge[0])][1][self.attribute+"_"+str(self.centrality_cutoff)]
				node_to = data_nodes[nodes.index(edge[1])][1][self.attribute+"_"+str(self.centrality_cutoff)]
				average = (((np.float(node_from) + np.float(node_to)) / 2))
				edge[2][self.attribute+"_"+str(self.centrality_cutoff)] = average

		if self.centrality_type == 'betweenness':
			cc = self.G_ig.edge_betweenness(directed=True, cutoff=None, weights=self.weight)
			cc_dict = dict(zip(self.G.edges, [np.float(i) for i in cc]))
			nx.set_edge_attributes(self.G, cc_dict, self.centrality_type+"_"+str(self.centrality_cutoff))

	def save_graph(self):
		#ox.save_graph_shapefile(self.G, filename=self.city+'_'+self.attribute)
		ox.save_graphml(self.G, filepath="data/"+self.city+'_'+self.attribute)

	def set_colors(self, att_name = 'closeness'):
		self.att_name = att_name

		# list of edge values for the orginal graph
		ev = list(nx.get_edge_attributes(self.G, self.att_name+"_"+str(self.centrality_cutoff)).values())

		# list of node values for the orginal graph
		nv = list(nx.get_node_attributes(self.G, self.att_name+"_"+str(self.centrality_cutoff)).values())
			
		# color scale converted to list of colors for graph edges
		norm_ev = colors.Normalize(vmin=min(ev), vmax=max(ev))
		cmap_ev = cm.ScalarMappable(norm=norm_ev, cmap=cm.inferno)

		# color scale converted to list of colors for graph nodes
		norm_nv = colors.Normalize(vmin=min(nv), vmax=max(nv))
		cmap_nv = cm.ScalarMappable(norm=norm_nv, cmap=cm.inferno)

		for edge in self.G.edges(data=True):
			edge[2]['color'] = cmap_ev.to_rgba(edge[2][self.att_name+"_"+str(self.centrality_cutoff)])
		for node in self.G.nodes(data=True):
			node[1]['color'] = cmap_nv.to_rgba(node[1][self.att_name+"_"+str(self.centrality_cutoff)])
			
		self.ec = list(nx.get_edge_attributes(self.G, 'color').values())
		self.nc = list(nx.get_node_attributes(self.G, 'color').values())

	def plot_graph(self, geometry):
		if geometry=='edge':
			fig, ax = ox.plot_graph(self.G, bgcolor='k', node_size=0, node_color='w', 
									node_edgecolor='gray', node_zorder=2,save=True,show=False,
									edge_color=self.ec , edge_linewidth=.5, edge_alpha=1,
									filepath="images/"+str(self.city)+'_edge_'+self.attribute+'_'+\
									str(self.centrality_cutoff)+".png", dpi=300)
		if geometry=='node':
			fig, ax = ox.plot_graph(self.G, bgcolor='k', node_size=0.5, save=True, 
									show=False, node_color=self.nc , edge_color='gray', 
									node_zorder=2, node_edgecolor=self.nc , edge_linewidth=0, 
									edge_alpha=0.5, filepath="images/"+str(self.city)+'_node_'+self.attribute+'_'
									+str(self.centrality_cutoff)+".png", dpi=300)

if __name__ == '__main__':
	city_name = sys.argv[1]
	city_bbox = list(map(float, sys.argv[3].strip('[]').split(',')))
	create_by = sys.argv[2]
	centrality_type = sys.argv[4]
	centrality_cutoff = int(sys.argv[5])


	#my_file = Path("data/"+city_name+"_"+centrality_type)
	my_file = Path("data/"+city_name+"_"+centrality_type+"_"+str(centrality_cutoff))
	print(my_file)
	city = Centrality(city_name, city_bbox)
	if my_file.is_file():
		print("Existing Graph Found!")
		city.load_network(centrality_type)
	else:
		city.create_network(create_by)
	city.calculate_node_centrality(centrality_type, centrality_cutoff)
	city.calculate_edge_centrality(centrality_type)
	city.save_graph()
	city.set_colors(centrality_type)
	city.plot_graph('edge')
	city.plot_graph('node')







