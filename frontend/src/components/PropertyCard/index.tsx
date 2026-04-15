import React from 'react';
import { FaBed, FaBath, FaRulerCombined } from 'react-icons/fa';

interface Property {
  id: string;
  title: string;
  description: string;
  price: number;
  area: number;
  rooms: number;
  bathrooms: number;
  location: string;
  city: string;
  state: string;
  zip_code: string;
  property_type: string;
  images: string[];
}

interface Props {
  property: Property;
  compact?: boolean;
}

const PropertyCard: React.FC<Props> = ({ property, compact = false }) => {
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(price);
  };

  if (compact) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-3 hover:shadow-md transition-shadow">
        <h3 className="font-semibold text-gray-800 truncate">{property.title}</h3>
        <p className="text-blue-600 font-bold">{formatPrice(property.price)}</p>
        <p className="text-sm text-gray-500">{property.city}, {property.state}</p>
        <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
          <span className="flex items-center"><FaBed className="mr-1" /> {property.rooms}</span>
          <span className="flex items-center"><FaBath className="mr-1" /> {property.bathrooms}</span>
          <span className="flex items-center"><FaRulerCombined className="mr-1" /> {property.area} sqft</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
      <div className="h-48 bg-gray-200">
        {property.images && property.images[0] ? (
          <img src={property.images[0]} alt={property.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">No image</div>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-lg text-gray-800 mb-1">{property.title}</h3>
        <p className="text-blue-600 text-xl font-bold mb-2">{formatPrice(property.price)}</p>
        <p className="text-gray-600 mb-3">{property.location}</p>
        <div className="flex items-center gap-4 text-gray-700">
          <span className="flex items-center"><FaBed className="mr-1" /> {property.rooms} beds</span>
          <span className="flex items-center"><FaBath className="mr-1" /> {property.bathrooms} baths</span>
          <span className="flex items-center"><FaRulerCombined className="mr-1" /> {property.area} sqft</span>
        </div>
        <p className="text-sm text-gray-500 mt-2 line-clamp-2">{property.description}</p>
      </div>
    </div>
  );
};

export default PropertyCard;