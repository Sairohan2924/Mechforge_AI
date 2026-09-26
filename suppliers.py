from __future__ import annotations

def quote_supplier(supplier, analysis, quantity):
    minutes=float(analysis.get('minutes',10.0)); material=float(analysis.get('cost_low',100))/max(quantity,1)
    setup=float(supplier.get('setup_cost',1500)); rate=float(supplier.get('machine_rate',900)); mf=float(supplier.get('material_factor',1.0));
    unit=(minutes/60*rate + material*mf) + setup/max(quantity,1)
    unit*=1.05
    total=unit*quantity
    return {'supplier':supplier['name'],'unit_cost':unit,'total_cost':total,'lead_days':int(supplier.get('lead_days',7)), 'notes':f"Machine rate ₹{rate:,.0f}/h, setup ₹{setup:,.0f}, material factor {mf:.2f}."}
