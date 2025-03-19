def summarizing_prompt(text: str):
    return f"""
Summarize for me the following:
what is cost of the room, what is the czynsz cost, additional costs, and whether are there available with animals.
Your answer has to be in the following format and only with text:
Summary of Rental Information:

*Rental Cost*: [PRICE] zl (Monthly) // remain unknown if not specified
*Czynsz cost*: [COST] zl (Monthly) // remain unknown if not specified
*First payment*: [ADDITIONAL] zł (Monthly)  //  first payment unknown if not specified
*Animals Friendly*: TRUE/FALSE // remain unknown if not specified

*Additional Insights*:
// add there *Additional Insights
Example:
    Summary of Rental Information:

    *Rental Cost*: 2100zł (Monthly)
    *Czynsz cost*: 200zł (Monthly)
    *First payment*: 2300 once
    *Animals Friendly*: Not specified

Notes:
- Chynsz is always lower than rental cost. sometimes it is provided like 2100 + 500, then usually '500' is Czynsz.
- Additional costs: usually it is one time payment.
- Dont add any text except the format specified above.
- Make sure Chynsz is not same as rental cost, Chynsz are fees like water/electricity/internet and others, here is the complete definition for you:
In Poland, "czynsz" refers to the rent or a regular fee paid by tenants to landlords or by property owners to housing cooperatives or community associations. Its meaning can vary depending on the context.
- If Chynsz specified is more than rental cost, or it seems for you like it is too much (not more than 1000), and other payments included, add them up and substract from the rental cost
text: {text}
"""
