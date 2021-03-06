# file: cartesianMesh.py
# author: Olivier Mesnard (mesnardo@gwu.edu)
# description: Implementation of the class `CartesianStructuredMesh` 
#              and its sub-classes.


import os
import sys
import math
from operator import mul
from decimal import Decimal

import numpy
import yaml


class Segment(object):
  """Contains information about a segment."""
  def __init__(self, data=None, vertices=None):
    """Creates the segment vertices.

    Parameters
    ----------
    data: dictionary, optional
      YAML data;
      default: None.
    vertices: 1D array of floats, optional
      vertices along the segment;
      default: None.
    """
    if data:
      self.create_from_yaml_data(data)
    elif numpy.all(vertices):
      self.create_from_vertices(vertices)
    self.nb_divisions = self.vertices.size-1

  def create_from_vertices(self, vertices):
    """"Stores vertices."""
    self.vertices = vertices

  def create_from_yaml_data(self, data):
    """Creates vertices from provided YAML data.

    Parameters
    ----------
    data: dictionary
      YAML data.
    """
    self.start, self.end = data['start'], data['end']
    self.width = data['width']
    self.stretch_ratio = self.get_stretch_ratio(self.width,
                                                stretch_ratio=data['stretchRatio'], 
                                                aspect_ratio=data['aspectRatio'],
                                                precision=data['precision'])
    self.vertices = self.get_vertices(reverse=data['reverse'])

  def print_parameters(self):
    """Prints the parameters of the segment."""
    print('\n[info] printing parameters of segment ...')
    print('\tlimits: [{}, {}]'.format(self.start, self.end))
    print('\treal limits: [{}, {}]'.format(self.vertices[0], self.vertices[-1]))
    print('\tstretching ratio: {}'.format(self.stretch_ratio))
    print('\taspect ratio: {}'.format(self.aspect_ratio))
    print('\tnumber of divisions: {}\n'.format(self.nb_divisions))

  def get_vertices(self, reverse=False):
    """Computes the vertices of the segment.

    Parameters
    ----------
    reverse: boolean, optional
      Set 'True' if you want to reverse the stretching order;
      default: False.

    Returns
    -------
    vertices: 1D array of floats
      The vertices of the segment.
    """
    length = abs(self.end-self.start)
    width = self.width
    ratio = self.stretch_ratio
    if abs(ratio-1.0) < 1.0E-06:
      # uniform discretization
      self.aspect_ratio = 1.0
      if abs(int(round(length/width))-length/width) > 1.0E-12:
        print('[error] uniform discretization: '
              'length of the segment should be a multiple of the width provided')
        sys.exit(0)
      return numpy.arange(self.start, self.end+width/2.0, width)
    # stretched discretization
    n = int(round(math.log(1.0-length/width*(1.0-ratio))/math.log(ratio)))
    widths = numpy.empty(n, dtype=numpy.float64)
    widths[0], widths[1:] = width, ratio
    widths = numpy.cumprod(widths)
    # compute the aspect ratio
    self.aspect_ratio = widths[-1]/widths[0]
    # return the vertices
    if reverse:
      # inverse the stretching ratio and reverse the widths
      self.stretch_ratio = 1.0/ratio
      return numpy.insert(self.end-numpy.cumsum(widths), 0, self.end)[::-1]
    else:
      return numpy.insert(self.start+numpy.cumsum(widths), 0, self.start)

  def get_stretch_ratio(self, width, 
                        stretch_ratio=1.0, aspect_ratio=1.0, precision=6):
    """Computes the optimal stretching ratio given a targeted stretching ratio 
    or a targeted aspect ratio.

    Parameters
    ----------
    width: float
      Width of the first division.
    stretch_ratio: float, optional
      Targeted stretching ratio;
      default: 1.0.
    aspect_ratio: float, optional
      Targeted aspect ratio between the first and last divisions;
      default: 1.0.
    precision: integer, optional
      Precision of the optimal stretching ratio to compute;
      default: 6.

    Returns
    -------
    ratio: float
      The optimal stretching ratio.
    """
    # if stretching ratio provided
    if abs(stretch_ratio-1.0) > 1.0E-06:
      return self.compute_optimal_stretch_ratio(width, stretch_ratio, 
                                                precision=precision)
    # if aspect ratio provided
    elif abs(aspect_ratio-1.0) > 1.0E-06:
      ratio = self.compute_stretch_ratio(width, aspect_ratio,
                                         precision=precision)
      return self.compute_optimal_stretch_ratio(width, ratio, 
                                                precision=precision)
    # uniform discretization
    else:
      return 1.0

  def compute_stretch_ratio(self, width, aspect_ratio, 
                            precision=6):
    """Computes the stretching ratio provided the a targeted aspect ratio 
    between the first and last divisions of the segment.

    Parameters
    ----------
    width: float
      Width of the first division.
    aspect_ratio: float
      Targeted aspect ratio.
    precision: integer, optional
      Precision of the stretching ratio to compute;
      default: 6.

    Returns
    -------
    ratio: float
      The stretching ratio.
    """
    length = abs(self.end-self.start)
    current_precision = 1
    ratio = 2.0
    while current_precision < precision:
        n = int(round(math.log(1.0-length/width*(1.0-ratio))/math.log(ratio)))
        candidate_aspect_ratio = ratio**(n-1)
        if candidate_aspect_ratio < aspect_ratio:
            ratio += (0.1)**current_precision
            current_precision += 1
        else:
            ratio -= (0.1)**current_precision
    return ratio

  def compute_optimal_stretch_ratio_old(self, width, ratio, 
                                        precision=6):
    """***DEPRECATED***
    Computes the optimal stretching ratio provided a targeted one.

    Parameters
    ----------
    width: float
      Width of the first division of the segment.
    ratio: float
      Targeted stretching ratio.
    precision: integer, optional
      Precision of the stretching ratio to compute;
      default: 6.

    Returns
    -------
    ratio: float
      The optimal stretching ratio.
    """
    length = abs(self.end-self.start)
    precision_ratio = abs(Decimal(str(ratio)).as_tuple().exponent)
    while precision_ratio < precision:
      try:
        n = int(round(math.log(1.0-(1.0-ratio)*length/width)/math.log(ratio)))
        candidate_length = width*(1.0-ratio**n)/(1.0-ratio)
      except:
        candidate_length = 0.0
      if candidate_length < length:
        ratio += (0.1)**precision_ratio
        precision_ratio += 1
      else:
        ratio -= (0.1)**precision_ratio
    return ratio

  def compute_optimal_stretch_ratio(self, width, ratio, 
                                    precision=6):
    """Computes the optimal stretching ratio provided a targeted one.

    Parameters
    ----------
    width: float
      Width of the first division of the segment.
    ratio: float
      Targeted stretching ratio.
    precision: integer, optional
      Precision of the stretching ratio to compute;
      default: 6.

    Returns
    -------
    ratio: float
      The optimal stretching ratio.
    """
    def geometric_sum(a, r, n):
      """Computes the sum of the geometric progression."""
      return a*(1.0-r**n)/(1.0-r)
    length = abs(self.end-self.start)
    precision_ratio = abs(Decimal(str(ratio)).as_tuple().exponent)
    while precision_ratio < precision:      
      n = int(math.log(1.0-(1.0-ratio)*length/width)/math.log(ratio))
      deviation_inf = abs(length - geometric_sum(width, ratio, n))
      deviation_sup = abs(length - geometric_sum(width, ratio, n+1))
      precision_ratio += 1
      if deviation_inf < deviation_sup:
        ratio += 0.1**precision_ratio
      else:
        ratio -= 0.1**precision_ratio
    return ratio

  def generate_yaml_info(self):
    """Generates a dictionary with segment's information ready for YAML.

    The dictionary contains the end, the number of divisions, and the stretching
    ratio of the segment.
    """
    info = {}
    info['end'] = self.end
    info['cells'] = self.nb_divisions
    info['stretchRatio'] = self.stretch_ratio
    return info


class GridLine(object):
  """Contains information about a gridline."""
  def __init__(self, data=None, vertices=None, label=None):
    """Creates a gridline from provided YAML data or vertices.

    Parameters
    ----------
    data: dictionary, optional
      YAML data about the gridline;
      default: None.
    vertices: 1D array of floats, optional
      Vertices along the gridline;
      default: None.
    label: string, optional
      Label of the direction;
      default: None.
    """
    self.label = label
    self.segments = []
    if data:
      self.create_from_yaml_data(data)
    elif numpy.all(vertices):
      self.create_from_vertices(vertices)
    self.nb_divisions = sum(segment.nb_divisions for segment in self.segments)

  def create_from_vertices(self, vertices):
    """Defines the gridline from provided vertices as a single segment.

    Parameters
    ----------
    vertices: 1D array of floats
      The vertices along the gridline.
    """
    self.start, self.end = vertices[0], vertices[-1]
    self.segments.append(Segment(vertices=vertices))

  def create_from_yaml_data(self, data):
    """Initializes the gridline parameters and computes its vertices.

    A gridline is defined as a sequence of uniform and/or stretched segments.

    Parameters
    ----------
    data: dictionary
      Parameters of the gridline in a YAML format.
    """
    self.label = data['direction']
    self.start = data['start']
    self.end = data['subDomains'][-1]['end']
    for index, node in enumerate(data['subDomains']):
      # store starting point
      data['subDomains'][index]['start'] = (data['start'] if index == 0
                                            else data['subDomains'][index-1]['end'])
      # set default parameters if not present
      if 'reverse' not in node.keys():
        data['subDomains'][index]['reverse'] = False
      if 'precision' not in node.keys():
        data['subDomains'][index]['precision'] = 6
      if 'aspectRatio' not in node.keys():
        data['subDomains'][index]['aspectRatio'] = 1.0
      if 'stretchRatio' not in node.keys():
        data['subDomains'][index]['stretchRatio'] = 1.0
      # create a segment
      self.segments.append(Segment(data=node))

  def get_vertices(self, precision=6):
    """Gets the vertices removing the repeated values at boundaries 
    between consecutive segments.

    Parameters
    ----------
    precision: integer, optional
      Precision used to round the vertices so we can remove repeated values;
      default: 6.

    Returns
    -------
    vertices: 1D array of floats
      The vertices along the gridline.
    """
    return numpy.unique(numpy.concatenate(([numpy.round(segment.vertices, 
                                                        precision) 
                                            for segment in self.segments])))

  def print_parameters(self):
    """Prints parameters of the gridline."""
    print('[info] printing parameters of the gridline {} ...'.format(self.label))
    vertices = self.get_vertices()
    print('\tlimits: [{}, {}]'.format(self.start, self.end))
    print('\treal limits: [{}, {}]'.format(vertices[0], vertices[-1]))
    print('\tnumber of divisions: {}'.format(self.nb_divisions))
    for segment in self.segments:
      segment.print_parameters()

  def generate_yaml_info(self):
    """Generates a dictionary with gridline's information ready for YAML.

    The dictionary contains the direction, the start, and segments information
    of the gridline.
    """
    info = {}
    info['direction'] = self.label
    info['start'] = self.start
    info['subDomains'] = []
    for segment in self.segments:
      info['subDomains'].append(segment.generate_yaml_info())
    return info


class CartesianStructuredMesh(object):
  """Contains info related to a Cartesian structured mesh 
  (stretched or uniform).
  """
  def __init__(self):
    """Instantiates an empty mesh."""
    self.gridlines = []

  def get_number_cells(self):
    """Gets the number of divisions along each gridline 
    and the total number of cells.
    """
    nb_divisions = []
    for gridline in self.gridlines:
      nb_divisions.append(gridline.nb_divisions)
    return reduce(mul, nb_divisions, 1), nb_divisions

  def create(self, data):
    """Creates the gridlines.

    Parameters
    ----------
    data: list of dictionaries
      Contains YAML information about the gridlines.
    """
    print('[info] generating Cartesian grid ...')
    for node in data:
      self.gridlines.append(GridLine(data=node))

  def print_parameters(self):
    """Prints parameters of the Cartesian structured mesh."""
    print('[info] printing parameters of the Cartesian structured mesh ...')
    nb_cells, _ = self.get_number_cells()
    print('\tnumber of cells: {}'.format(nb_cells))
    for gridline in self.gridlines:
      gridline.print_parameters()

  def write(self, file_path, precision=6):
    """Writes the gridlines into a file.

    The first line of the file contains the number of divisions 
    along each gridline.
    Then the vertices along each gridline are written in single column 
    starting with the first gridline.

    Parameters
    ----------
    file_path: string
      Path of the file to write in.
    precision: integer, optional
      Precision at which the vertices will be written;
      default: 6.
    """
    print('[info] writing vertices into {} ...'.format(file_path))
    _, nb_cells_directions = self.get_number_cells()
    with open(file_path, 'w') as outfile:
      outfile.write('\t'.join(str(nb) for nb in nb_cells_directions)+'\n')
      for gridline in self.gridlines:
        numpy.savetxt(outfile, gridline.get_vertices(precision=precision))

  def read(self, file_path):
    """Reads the coordinates from the file.

    Parameters
    ----------
    file_name: string
      Name of file containing grid-node stations along each direction.
    """
    print('[info] reading vertices from {} ...'.format(file_path))
    with open(file_path, 'r') as infile:
      nb_divisions = numpy.array([int(n) for n in infile.readline().strip().split()])
      vertices = numpy.loadtxt(infile, dtype=numpy.float64)
    vertices = numpy.array(numpy.split(vertices, numpy.cumsum(nb_divisions[:-1]+1)))
    labels = ['x', 'y', 'z']
    for index, vertices_gridline in enumerate(vertices):
      self.gridlines.append(GridLine(vertices=vertices_gridline, 
                                     label=labels[index]))

  def read_yaml_file(self, file_path):
    """Parses the YAML file.

    Parameters
    ----------
    file_path: string
      Path the YAML file.

    Returns
    -------
    data: list of dictionaries
      Parsed YAML information.
    """
    print('[info] reading grid parameters from {} ...'.format(file_path))
    with open(file_path, 'r') as infile:
      return yaml.load(infile)

  def write_yaml_file(self, file_path):
    """Writes a YAML readable file with information 
    about the Cartesian structured mesh.

    Parameters
    ----------
    file_path: string
      Path of the file to write.
    """
    print('[info] writing grid parameters into {} ...'.format(file_path))
    data = []
    for gridline in self.gridlines:
      data.append(gridline.generate_yaml_info())
    nb_cells, nb_cells_directions = self.get_number_cells()
    with open(file_path, 'w') as outfile:
      outfile.write('# {}\n'.format(os.path.basename(file_path)))
      outfile.write('# {} = {}\n\n'.format('x'.join(str(nb) for nb in nb_cells_directions), 
                                         nb_cells))
      outfile.write(yaml.dump(data, default_flow_style=False))