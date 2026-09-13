import type { BusinessInput } from "../types";

/** Quick-fill examples for the business input form -- Sakura Bakery is
 * fictional (matches the backend's demo creator dataset), Din Tai Fung
 * is real and will come back Google-verified if GOOGLE_MAPS_API_KEY is
 * configured on the backend. */
export const exampleBusinesses: BusinessInput[] = [
  {
    business_name: "Sakura Bakery",
    business_type: "Korean bakery",
    location: "Arcadia, CA",
    description: "Small Korean bakery selling pastries, coffee, and fresh bread.",
    target_audience: "18-30 year olds",
    goal: "Get more local customers",
    budget: 300,
  },
  {
    business_name: "Din Tai Fung",
    business_type: "restaurant",
    location: "Arcadia, CA",
    description: "Taiwanese restaurant known for soup dumplings.",
    target_audience: "25-45 year olds",
    goal: "Get more local customers",
    budget: 300,
  },
];

export const emptyBusinessInput: BusinessInput = {
  business_name: "",
  business_type: "",
  location: "",
  description: "",
  target_audience: "",
  goal: "",
  budget: 300,
};
