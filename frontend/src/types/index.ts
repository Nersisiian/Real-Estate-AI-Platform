export interface Property {
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

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}