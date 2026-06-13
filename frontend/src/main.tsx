import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./styles.css";

import Layout from "./components/Layout";
import SubmitClaim from "./pages/SubmitClaim";
import ReviewClaims from "./pages/ReviewClaims";
import EvalRunner from "./pages/EvalRunner";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <SubmitClaim /> },
      { path: "review", element: <ReviewClaims /> },
      { path: "eval", element: <EvalRunner /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
