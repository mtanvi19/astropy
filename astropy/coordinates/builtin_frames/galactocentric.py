# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import warnings

import numpy as np

from ... import units as u
from ...utils.exceptions import AstropyDeprecationWarning
from ..angles import Angle
from ..matrix_utilities import rotation_matrix, matrix_product, matrix_transpose
from ..representation import (CartesianRepresentation,
                              CartesianDifferential,
                              UnitSphericalRepresentation)
from ..baseframe import (BaseCoordinateFrame, frame_transform_graph,
                         RepresentationMapping)
from ..frame_attributes import FrameAttribute, CoordinateAttribute
from ..transformations import AffineTransform
from ..errors import ConvertError

from .icrs import ICRS

# Measured by minimizing the difference between a plane of coordinates along
#   l=0, b=[-90,90] and the Galactocentric x-z plane
# This is not used directly, but accessed via `get_roll0`.  We define it here to
# prevent having to create new Angle objects every time `get_roll0` is called.
_ROLL0 = Angle(58.5986320306*u.degree)

# RA,Dec : Reid et al. 2004 - http://adsabs.harvard.edu/abs/2004ApJ...616..872R.
# distance : Gillessen et al. 2009
# pm_ra, pm_dec : Reid & Brunthaler 2004 (assuming all motion is in the plane)
# radial velocity : Bovy et al. 2012 (negative of value is intentional)
galcen_default = ICRS(ra=266.4051*u.degree, dec=-28.936175*u.degree,
                      distance=8.3*u.kpc,
                      pm_ra=3.3236424408301515*u.mas/u.yr, # Converted Galactic
                      pm_dec=5.444726065240803*u.mas/u.yr, # to ICRS
                      radial_velocity=10*u.km/u.s)

class Galactocentric(BaseCoordinateFrame):
    r"""
    A coordinate or frame in the Galactocentric system. This frame
    requires specifying the Sun-Galactic center distance, and optionally
    the height of the Sun above the Galactic midplane.

    The position of the Sun is assumed to be on the x axis of the final,
    right-handed system. That is, the x axis points from the position of
    the Sun projected to the Galactic midplane to the Galactic center --
    roughly towards :math:`(l,b) = (0^\circ,0^\circ)`. For the default
    transformation (:math:`{\rm roll}=0^\circ`), the y axis points roughly
    towards Galactic longitude :math:`l=90^\circ`, and the z axis points
    roughly towards the North Galactic Pole (:math:`b=90^\circ`).

    The default position of the Galactic Center in ICRS coordinates is
    taken from Reid et al. 2004,
    http://adsabs.harvard.edu/abs/2004ApJ...616..872R.

    .. math::

        {\rm RA} = 17:45:37.224~{\rm hr}\\
        {\rm Dec} = -28:56:10.23~{\rm deg}

    The default distance to the Galactic Center is 8.3 kpc, e.g.,
    Gillessen et al. 2009,
    http://adsabs.harvard.edu/abs/2009ApJ...692.1075G.

    The default height of the Sun above the Galactic midplane is taken to
    be 27 pc, as measured by
    http://adsabs.harvard.edu/abs/2001ApJ...553..184C.

    For a more detailed look at the math behind this transformation, see
    the document :ref:`coordinates-galactocentric`.

    Parameters
    ----------
    representation : `BaseRepresentation` or None
        A representation object or None to have no data (or use the other
        keywords)
    galcen_distance : `~astropy.units.Quantity`, optional, must be keyword
        The distance from the Sun to the Galactic center.
    galcen_ra : `Angle`, optional, must be keyword
        The Right Ascension (RA) of the Galactic center in the ICRS frame.
    galcen_dec : `Angle`, optional, must be keyword
        The Declination (Dec) of the Galactic center in the ICRS frame.
    z_sun : `~astropy.units.Quantity`, optional, must be keyword
        The distance from the Sun to the Galactic midplane.
    roll : `Angle`, optional, must be keyword
        The angle to rotate about the final x-axis, relative to the
        orientation for Galactic. For example, if this roll angle is 0,
        the final x-z plane will align with the Galactic coordinates x-z
        plane. Unless you really know what this means, you probably should
        not change this!
    copy : bool, optional
        If `True` (default), make copies of the input coordinate arrays.
        Can only be passed in as a keyword argument.

    Examples
    --------
    To transform to the Galactocentric frame with the default
    frame attributes, pass the uninstantiated class name to the
    ``transform_to()`` method of a coordinate frame or
    `~astropy.coordinates.SkyCoord` object::

        >>> import astropy.units as u
        >>> import astropy.coordinates as coord
        >>> c = coord.ICRS(ra=[158.3122, 24.5] * u.degree,
        ...                dec=[-17.3, 81.52] * u.degree,
        ...                distance=[11.5, 24.12] * u.kpc)
        >>> c.transform_to(coord.Galactocentric) # doctest: +FLOAT_CMP
        <Galactocentric Coordinate (galcen_distance=8.3 kpc, galcen_ra=266d24m18.36s, galcen_dec=-28d56m10.23s, z_sun=27.0 pc, roll=0.0 deg): (x, y, z) in kpc
            [( -9.6083819 , -9.40062188,  6.52056066),
             (-21.28302307, 18.76334013,  7.84693855)]>

    To specify a custom set of parameters, you have to include extra keyword
    arguments when initializing the Galactocentric frame object::

        >>> c.transform_to(coord.Galactocentric(galcen_distance=8.1*u.kpc)) # doctest: +FLOAT_CMP
        <Galactocentric Coordinate (galcen_distance=8.1 kpc, galcen_ra=266d24m18.36s, galcen_dec=-28d56m10.23s, z_sun=27.0 pc, roll=0.0 deg): (x, y, z) in kpc
            [( -9.40785924,  -9.40062188,  6.52066574),
             (-21.08239383,  18.76334013,  7.84798135)]>

    Similarly, transforming from the Galactocentric frame to another coordinate frame::

        >>> c = coord.Galactocentric(x=[-8.3, 4.5] * u.kpc,
        ...                          y=[0., 81.52] * u.kpc,
        ...                          z=[0.027, 24.12] * u.kpc)
        >>> c.transform_to(coord.ICRS) # doctest: +FLOAT_CMP
        <ICRS Coordinate: (ra, dec, distance) in (deg, deg, kpc)
            [(  86.22349059, 28.83894138,  4.39157788e-05),
             ( 289.66802652, 49.88763881,  8.59640735e+01)]>

    Or, with custom specification of the Galactic center::

        >>> c = coord.Galactocentric(x=[-8.0, 4.5] * u.kpc,
        ...                          y=[0., 81.52] * u.kpc,
        ...                          z=[21.0, 24120.0] * u.pc,
        ...                          z_sun=21 * u.pc, galcen_distance=8. * u.kpc)
        >>> c.transform_to(coord.ICRS) # doctest: +FLOAT_CMP
        <ICRS Coordinate: (ra, dec, distance) in (deg, deg, kpc)
            [(  86.2585249 ,  28.85773187,  2.75625475e-05),
             ( 289.77285255,  50.06290457,  8.59216010e+01)]>

    """
    frame_specific_representation_info = {
        CartesianDifferential: [
            RepresentationMapping('d_x', 'v_x'),
            RepresentationMapping('d_y', 'v_y'),
            RepresentationMapping('d_z', 'v_z'),
        ],
    }

    default_representation = CartesianRepresentation
    default_differential = CartesianDifferential

    # frame attributes
    galcen = CoordinateAttribute(default=galcen_default, frame=ICRS)
    z_sun = FrameAttribute(default=27.*u.pc)
    roll = FrameAttribute(default=0.*u.deg)

    def __init__(self, *args, **kwargs):

        # backwards-compatibility
        if ('galcen_distance' in kwargs or 'galcen_ra' in kwargs or
                'galcen_dec' in kwargs):
            warnings.warn("The arguments 'galcen_distance', 'galcen_ra', and "
                          "'galcen_dec' are deprecated in favor of specifying "
                          "the full-space position and velocity of the Galactic "
                          "center by passing a frame in to the 'galcen' attribute",
                          AstropyDeprecationWarning)

        galcen_kw = dict()
        galcen_kw['distance'] = kwargs.pop('galcen_distance',
                                           self.galcen.distance)
        galcen_kw['ra'] = kwargs.pop('galcen_ra', self.galcen.ra)
        galcen_kw['dec'] = kwargs.pop('galcen_dec', self.galcen.dec)
        galcen_kw['pm_ra'] = self.galcen.pm_ra
        galcen_kw['pm_dec'] = self.galcen.pm_dec
        galcen_kw['radial_velocity'] = self.galcen.radial_velocity
        kwargs['galcen'] = ICRS(**galcen_kw)

        super(Galactocentric, self).__init__(self, *args, **kwargs)

    @property
    def galcen_ra(self):
        return self.galcen.frame.ra

    @property
    def galcen_dec(self):
        return self.galcen.frame.dec

    @property
    def galcen_distance(self):
        return self.galcen.frame.distance

    @classmethod
    def get_roll0(cls):
        """
        The additional roll angle (about the final x axis) necessary to align
        the final z axis to match the Galactic yz-plane.  Setting the ``roll``
        frame attribute to  -this method's return value removes this rotation,
        allowing the use of the `Galactocentric` frame in more general contexts.
        """
        # note that the actual value is defined at the module level.  We make at
        # a property here because this module isn't actually part of the public
        # API, so it's better for it to be accessable from Galactocentric
        return _ROLL0

# ICRS to/from Galactocentric ----------------------->
def get_matrix_vectors(galactocentric_frame):
    # shorthand
    gcf = galactocentric_frame

    # define rotation matrix to align x(ICRS) with the vector to the Galactic center
    mat1 = rotation_matrix(-gcf.galcen_dec, 'y')
    mat2 = rotation_matrix(gcf.galcen_ra, 'z')
    # extra roll away from the Galactic x-z plane
    mat0 = rotation_matrix(gcf.get_roll0() - gcf.roll, 'x')

    # construct transformation matrix and use it
    R = matrix_product(mat0, mat1, mat2)

    # Now need to translate by Sun-Galactic center distance around x' and
    # rotate about y' to account for tilt due to Sun's height above the plane
    translation = CartesianRepresentation(gcf.galcen_distance * [1., 0., 0.])
    z_d = gcf.z_sun / gcf.galcen_distance
    H = rotation_matrix(-np.arcsin(z_d), 'y')

    # compute total matrices
    A = matrix_product(H, R)

    # Now we re-align the translation vector to account for the Sun's height
    # above the midplane
    offset = -translation.transform(H)

    # TODO: need to get the velocity offset and save as a differential on
    #       `offset` - leaving this to the next PR
    # vel_vec = matrix_product(H, -gcf.v_sun.xyz)

    return A, offset

@frame_transform_graph.transform(AffineTransform, ICRS, Galactocentric)
def icrs_to_galactocentric(icrs_coord, galactocentric_frame):
    if isinstance(icrs_coord.data, UnitSphericalRepresentation):
        raise ConvertError("Transforming to a Galactocentric frame requires "
                           "a 3D coordinate, e.g. (angle, angle, distance) or"
                           " (x, y, z).")

    return get_matrix_vectors(galactocentric_frame)

@frame_transform_graph.transform(AffineTransform, Galactocentric, ICRS)
def galactocentric_to_icrs(galactocentric_coord, icrs_frame):
    if isinstance(galactocentric_coord.data, UnitSphericalRepresentation):
        raise ConvertError("Transforming from a Galactocentric frame requires "
                           "a 3D coordinate, e.g. (angle, angle, distance) or"
                           " (x, y, z).")

    A, offset = get_matrix_vectors(galactocentric_coord)

    # the inverse of a rotation matrix is a transpose, which is much faster and
    #   more stable to compute
    A_T = matrix_transpose(A)
    return A_T, -offset.transform(A_T)
